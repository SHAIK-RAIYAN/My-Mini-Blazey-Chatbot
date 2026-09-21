import json
from typing import Any
from langchain.tools import tool
from app.clients.task_client import TaskClient
from app.models.task_models import (
    CreateTaskArgs,
    ListTasksArgs,
    UpdateTaskArgs,
    BulkUpdateTasksArgs,
)

task_client = TaskClient()

def _clean_payload(data: Any) -> Any:
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            return _clean_payload(parsed)
        except Exception:
            return data
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if value is None or value == "":
                continue
            if key in ("history", "auditLogs", "revisions", "rawTokens", "systemMeta", "__v"):
                continue
            cleaned_val = _clean_payload(value)
            if cleaned_val is not None and cleaned_val != {} and cleaned_val != []:
                cleaned[key] = cleaned_val
        return cleaned
    if isinstance(data, list):
        return [_clean_payload(item) for item in data[:20] if item is not None]
    return data

def project_tool_output(data: Any) -> str:
    cleaned = _clean_payload(data)
    if not isinstance(cleaned, dict):
        cleaned = {"data": cleaned} if cleaned else {}
    return json.dumps(cleaned, separators=(",", ":"))

@tool(description="Create a personal task with title and optional details", args_schema=CreateTaskArgs)
async def create_personal_task(
    title: str,
    description: str | None = None,
    taskType: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> str:
    payload: dict[str, Any] = {"title": title}
    if description is not None:
        payload["description"] = description
    if taskType is not None:
        payload["taskType"] = taskType
    if assignee is not None:
        payload["assignee"] = assignee
    if priority is not None:
        payload["priority"] = priority
    if status is not None:
        payload["status"] = status
    result = await task_client.create_task(payload)
    return project_tool_output(result)

@tool(description="List tasks with optional filters", args_schema=ListTasksArgs)
async def list_tasks(
    taskNumbers: list[str] | None = None,
    assignees: list[str] | None = None,
    page: int | None = 1,
    limit: int | None = 20,
    status: str | None = None,
) -> str:
    params: dict[str, Any] = {}
    if taskNumbers is not None:
        params["taskNumbers"] = taskNumbers
    if assignees is not None:
        params["assignees"] = assignees
    if page is not None:
        params["page"] = page
    if limit is not None:
        params["limit"] = limit
    if status is not None:
        params["status"] = status
    result = await task_client.list_tasks(params)
    return project_tool_output(result)

@tool(description="Update a single task by ID", args_schema=UpdateTaskArgs)
async def update_task_by_id(
    task_id: str,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    dueDate: str | None = None,
) -> str:
    payload: dict[str, Any] = {}
    if status is not None:
        payload["status"] = status
    if priority is not None:
        payload["priority"] = priority
    if assignee is not None:
        payload["assignee"] = assignee
    if dueDate is not None:
        payload["dueDate"] = dueDate
    result = await task_client.update_single_task(task_id, payload)
    return project_tool_output(result)

@tool(description="Bulk update multiple tasks at once", args_schema=BulkUpdateTasksArgs)
async def bulk_update_tasks(
    ids: list[str],
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
) -> str:
    payload: dict[str, Any] = {"ids": ids}
    if status is not None:
        payload["status"] = status
    if priority is not None:
        payload["priority"] = priority
    if assignee is not None:
        payload["assignee"] = assignee
    result = await task_client.bulk_update_tasks(payload)
    return project_tool_output(result)
