import json
from typing import Any
from langchain.tools import tool
from app.clients.task_client import TaskClient
from app.core.sanitizer import project_tool_output
from app.models.task_models import (
    CreateTaskArgs,
    ListTasksArgs,
    UpdateTaskArgs,
    BulkUpdateTasksArgs,
)

task_client = TaskClient()

@tool(description="Create a personal task with title and optional details", args_schema=CreateTaskArgs)
async def create_personal_task(
    title: str,
    description: str | None = None,
    taskType: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> str:
    """Create a personal task record directly using provided attributes."""
    try:
        payload: dict[str, Any] = {
            "title": title,
            "isPersonal": True,
        }
        if description is not None:
            payload["description"] = {"message": description, "linkedAttachment": []} if isinstance(description, str) else description
        if taskType is not None:
            payload["taskType"] = taskType
        if assignee:
            payload["assignee"] = assignee
            payload["assignees"] = [assignee]
        if priority is not None:
            payload["priority"] = priority
        if status is not None:
            payload["status"] = status

        result = await task_client.create_task(payload)
        return project_tool_output(result, "task")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="List tasks with optional filters", args_schema=ListTasksArgs)
async def list_tasks(
    taskNumbers: list[str] | None = None,
    assignees: list[str] | None = None,
    Scope: str | None = "PERSONAL",
    page: int | None = 1,
    limit: int | None = 20,
    status: str | None = None,
) -> str:
    """Retrieve personal or project tasks matching query parameters."""
    try:
        params: dict[str, Any] = {
            "Scope": Scope or "PERSONAL",
        }
        if taskNumbers:
            params["taskNumbers"] = ",".join(taskNumbers) if isinstance(taskNumbers, list) else str(taskNumbers)
        if assignees:
            params["assignees"] = ",".join(assignees) if isinstance(assignees, list) else str(assignees)
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        if status is not None:
            params["status"] = status
        result = await task_client.list_tasks(params)
        return project_tool_output(result, "task")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Update a single task by ID", args_schema=UpdateTaskArgs)
async def update_task_by_id(
    mongo_object_id: str,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    dueDate: str | None = None,
) -> str:
    """Update a specific task identified by its MongoDB ObjectId."""
    try:
        payload: dict[str, Any] = {}
        if status is not None:
            payload["status"] = status
        if priority is not None:
            payload["priority"] = priority
        if assignee is not None:
            payload["assignee"] = assignee
            payload["assignees"] = [assignee] if assignee else []
        if dueDate is not None:
            payload["dueDate"] = dueDate
        result = await task_client.update_single_task(mongo_object_id, payload)
        return project_tool_output(result, "task")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Bulk update multiple tasks at once", args_schema=BulkUpdateTasksArgs)
async def bulk_update_tasks(
    ids: list[str],
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
) -> str:
    """Bulk update multiple task records simultaneously."""
    try:
        payload: dict[str, Any] = {"ids": ids}
        if status is not None:
            payload["status"] = status
        if priority is not None:
            payload["priority"] = priority
        if assignee is not None:
            payload["assignee"] = assignee
            payload["assignees"] = [assignee] if assignee else []
        result = await task_client.bulk_update_tasks(payload)
        return project_tool_output(result, "task")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
