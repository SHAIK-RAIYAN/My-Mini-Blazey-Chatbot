import json as json_lib
import json
from typing import Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings, Settings
from app.core.logger import get_logger

logger = get_logger()

class APIException(Exception):
    def __init__(
        self,
        status_code: int,
        message: str | list[str],
        error: str,
        response_body: dict | None = None,
    ):
        self.status_code = status_code
        self.message = message
        self.error = error
        self.response_body = response_body or {}
        super().__init__(f"[{status_code}] {error}: {message}")

class BaseAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    def _get_token(self) -> str:
        if hasattr(settings, "JWT_TOKEN") and settings.JWT_TOKEN:
            return settings.JWT_TOKEN
        config_instance = Settings()
        return getattr(config_instance, "JWT_TOKEN", "")

    def _build_url(self, path: str) -> str:
        clean_path = path.lstrip("/")
        return f"{self.base_url}/{clean_path}" if clean_path else self.base_url

    def _get_headers(self, additional_headers: dict | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if additional_headers:
            headers.update(additional_headers)
        return headers

    def _handle_error_response(self, response: httpx.Response) -> None:
        try:
            body = response.json()
        except Exception:
            body = {}

        if isinstance(body, dict):
            status_code = body.get("statusCode", response.status_code)
            message = body.get("message", response.text)
            error = body.get("error", response.reason_phrase or "HTTP Error")
            raise APIException(
                status_code=int(status_code),
                message=message,
                error=str(error),
                response_body=body,
            )

        raise APIException(
            status_code=response.status_code,
            message=response.text,
            error=response.reason_phrase or "HTTP Error",
            response_body={},
        )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        reraise=True,
    )
    async def _execute_http_request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json_data: Any = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        logger.info(f"ACTUAL API CALL DISPATCHED | Method: {method} | URL: {url} | Payload: {json_data}")
        response = await self.client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=headers,
            **kwargs,
        )
        logger.info(f"API RESPONSE RECEIVED | Status: {response.status_code} | URL: {url}")
        if response.status_code == 503:
            raise httpx.HTTPStatusError("503 Service Unavailable", request=response.request, response=response)
        return response

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
        headers: dict | None = None,
        **kwargs,
    ) -> Any:
        url = self._build_url(path)
        request_headers = self._get_headers(headers)
        fallback_json = json_lib.dumps(
            {"status": "error", "code": 503, "message": "Upstream service disconnected."},
            separators=(",", ":"),
        )
        try:
            response = await self._execute_http_request(
                method=method,
                url=url,
                params=params,
                json_data=json,
                headers=request_headers,
                **kwargs,
            )
        except (httpx.ReadError, httpx.ConnectError, httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.error(f"HTTP Error during API call to {url}: {exc}")
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code != 503:
                try:
                    self._handle_error_response(exc.response)
                except APIException as api_exc:
                    logger.error(f"API Exception for {url}: {api_exc}")
                    err_dict = {
                        "statusCode": api_exc.status_code,
                        "error": api_exc.error,
                        "message": api_exc.message,
                    }
                    if isinstance(api_exc.response_body, dict):
                        for k, v in api_exc.response_body.items():
                            if k not in err_dict and v is not None:
                                err_dict[k] = v
                    return json_lib.dumps(err_dict, separators=(",", ":"))
            return fallback_json
        except APIException as exc:
            logger.error(f"API Exception for {url}: {exc}")
            if exc.status_code == 503:
                return fallback_json
            err_dict = {
                "statusCode": exc.status_code,
                "error": exc.error,
                "message": exc.message,
            }
            if isinstance(exc.response_body, dict):
                for k, v in exc.response_body.items():
                    if k not in err_dict and v is not None:
                        err_dict[k] = v
            return json_lib.dumps(err_dict, separators=(",", ":"))

        if response.status_code == 503:
            return fallback_json

        if response.is_error:
            try:
                self._handle_error_response(response)
            except APIException as exc:
                logger.error(f"API Error Response from {url} [Status {response.status_code}]: {exc}")
                if exc.status_code == 503:
                    return fallback_json
                err_dict = {
                    "statusCode": exc.status_code,
                    "error": exc.error,
                    "message": exc.message,
                }
                if isinstance(exc.response_body, dict):
                    for k, v in exc.response_body.items():
                        if k not in err_dict and v is not None:
                            err_dict[k] = v
                return json_lib.dumps(err_dict, separators=(",", ":"))

        if response.status_code == 204 or not response.content:
            return {}

        try:
            return response.json()
        except Exception:
            return {"data": response.text}

    async def get(self, path: str, *, params: dict | None = None, headers: dict | None = None, **kwargs) -> Any:
        return await self.request("GET", path, params=params, headers=headers, **kwargs)

    async def post(self, path: str, *, json: Any = None, params: dict | None = None, headers: dict | None = None, **kwargs) -> Any:
        return await self.request("POST", path, json=json, params=params, headers=headers, **kwargs)

    async def patch(self, path: str, *, json: Any = None, params: dict | None = None, headers: dict | None = None, **kwargs) -> Any:
        return await self.request("PATCH", path, json=json, params=params, headers=headers, **kwargs)

    async def put(self, path: str, *, json: Any = None, params: dict | None = None, headers: dict | None = None, **kwargs) -> Any:
        return await self.request("PUT", path, json=json, params=params, headers=headers, **kwargs)

    async def delete(self, path: str, *, params: dict | None = None, headers: dict | None = None, **kwargs) -> Any:
        return await self.request("DELETE", path, params=params, headers=headers, **kwargs)

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "BaseAPIClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

BaseAPIClient.request.retry = BaseAPIClient._execute_http_request.retry
