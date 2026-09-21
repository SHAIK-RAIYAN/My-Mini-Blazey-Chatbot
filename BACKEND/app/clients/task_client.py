from typing import Any
from app.config import settings
from app.clients.http_client import BaseAPIClient

class TaskClient(BaseAPIClient):
    def __init__(self, base_url: str | None = None):
        target_url = base_url or settings.PROJECT_API_BASE_URL
        super().__init__(base_url=target_url)

    async def create_task(self, payload: dict) -> dict:
        task_data = dict(payload)
        if not task_data.get("project"):
            task_data["isPersonal"] = True
        return await self.post("/task", json=task_data)

    async def list_tasks(self, params: dict | None = None) -> dict:
        query_params = dict(params or {})
        if "Scope" not in query_params and "scope" not in query_params:
            query_params["Scope"] = "PERSONAL"
        elif "scope" in query_params:
            query_params["Scope"] = query_params.pop("scope")

        if "flat" not in query_params:
            query_params["flat"] = "true"

        for key in ("taskNumber", "task_number", "task_numbers", "taskId", "task_id", "id", "ids"):
            if key in query_params:
                query_params["taskNumbers"] = query_params.pop(key)
                break

        for key in ("assignee", "assigned_to"):
            if key in query_params:
                query_params["assignees"] = query_params.pop(key)
                break

        return await self.get("/task", params=query_params)

    async def update_single_task(self, task_id: str, payload: dict) -> dict:
        return await self.patch(f"/task/multiple?ids={task_id}", json=payload)

    async def bulk_update_tasks(self, payload: dict) -> dict:
        return await self.patch("/task/multiple", json=payload)
