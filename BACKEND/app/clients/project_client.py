from typing import Any
import re
from app.config import settings
from app.clients.http_client import BaseAPIClient

class ProjectClient(BaseAPIClient):
    def __init__(self, base_url: str | None = None):
        target_url = base_url or settings.PROJECT_API_BASE_URL
        super().__init__(base_url=target_url)

    async def create_project(self, payload: dict) -> dict:
        return await self.post("/projects", json_data=payload)

    async def list_projects(self, params: dict | None = None) -> dict:
        query_params = dict(params or {})
        return await self.get("/projects", params=query_params)

    async def get_project(self, identifier: str) -> dict:
        clean_id = identifier.strip()
        if re.fullmatch(r"[0-9a-fA-F]{24}", clean_id):
            return await self.get("/projects", params={"id": clean_id})
        res = await self.get("/projects", params={"projectId": clean_id})
        data = res.get("data", []) if isinstance(res, dict) else []
        if data:
            return res
        return await self.get("/projects", params={"search": clean_id})

    async def update_project(self, project_id: str, payload: dict) -> dict:
        return await self.patch(f"/projects/{project_id}", json_data=payload)
