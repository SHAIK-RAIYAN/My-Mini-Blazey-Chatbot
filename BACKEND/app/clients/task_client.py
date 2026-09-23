from typing import Any
from app.config import settings
from app.clients.http_client import BaseAPIClient

class TaskClient(BaseAPIClient):
    def __init__(self, base_url: str | None = None):
        target_url = base_url or settings.PROJECT_API_BASE_URL
        super().__init__(base_url=target_url)

    async def create_task(self, payload: dict) -> dict:
        task_data = dict(payload)
        if "isPersonal" not in task_data:
            if task_data.get("project"):
                task_data["isPersonal"] = False
            else:
                task_data["isPersonal"] = True
        if not task_data.get("isPersonal") and "type" not in task_data:
            task_data["type"] = "Task"
        if "assignee" in task_data and "assignees" not in task_data:
            val = task_data["assignee"]
            if val:
                task_data["assignees"] = [val] if not isinstance(val, list) else val
        return await self.post("/task", json_data=task_data)

    async def list_tasks(self, params: dict | None = None) -> dict:
        query_params = dict(params or {})

        for p_key in ("projectIds", "projectId", "project"):
            if p_key in query_params:
                p_val = query_params.pop(p_key)
                if p_val and "projectIds" not in query_params:
                    query_params["projectIds"] = ",".join(p_val) if isinstance(p_val, list) else str(p_val)
                    if "Scope" not in query_params and "scope" not in query_params:
                        query_params["Scope"] = "PROJECT"

        for singular in ("number", "taskNumber", "task_number"):
            if singular in query_params:
                val = query_params.pop(singular)
                if "taskNumbers" not in query_params:
                    query_params["taskNumbers"] = val

        for singular in ("assignee", "assigned_to", "assignee_id"):
            if singular in query_params:
                val = query_params.pop(singular)
                if "assignees" not in query_params:
                    query_params["assignees"] = val

        if "Scope" not in query_params and "scope" not in query_params:
            query_params["Scope"] = "PERSONAL"
        elif "scope" in query_params:
            query_params["Scope"] = query_params.pop("scope")

        if isinstance(query_params.get("taskNumbers"), list):
            query_params["taskNumbers"] = ",".join(query_params["taskNumbers"])
        if isinstance(query_params.get("assignees"), list):
            query_params["assignees"] = ",".join(query_params["assignees"])

        if "flat" not in query_params:
            query_params["flat"] = "true"

        return await self.get("/task", params=query_params)

    async def update_single_task(self, task_id: str, payload: dict) -> dict:
        clean_payload = {k: v for k, v in payload.items() if k not in ("task_id", "id")}
        clean_payload["ids"] = [task_id]
        if "assignee" in clean_payload and "assignees" not in clean_payload:
            val = clean_payload["assignee"]
            if val:
                clean_payload["assignees"] = [val] if not isinstance(val, list) else val
            else:
                clean_payload["assignees"] = []
        return await self.patch("/task/multiple", params={"ids": task_id}, json_data=clean_payload)

    async def update_task_by_id(self, task_id: str, payload: dict) -> dict:
        return await self.update_single_task(task_id, payload)

    async def bulk_update_tasks(self, payload: dict) -> dict:
        clean_payload = dict(payload)
        ids = clean_payload.get("ids", [])
        ids_str = ",".join(ids) if isinstance(ids, list) else str(ids)
        if "assignee" in clean_payload and "assignees" not in clean_payload:
            val = clean_payload["assignee"]
            if val:
                clean_payload["assignees"] = [val] if not isinstance(val, list) else val
            else:
                clean_payload["assignees"] = []
        return await self.patch("/task/multiple", params={"ids": ids_str}, json_data=clean_payload)
