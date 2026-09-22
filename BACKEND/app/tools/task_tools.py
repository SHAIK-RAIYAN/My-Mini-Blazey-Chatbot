import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from langchain.tools import tool
from app.clients.task_client import TaskClient
from app.clients.employee_client import EmployeeClient
from app.core.sanitizer import project_tool_output
from app.models.task_models import (
    CreateTaskArgs,
    ListTasksArgs,
    UpdateTaskArgs,
    BulkUpdateTasksArgs,
)

task_client = TaskClient()
employee_client = EmployeeClient()

PRIORITY_MAP = {
    "urgent": "6a80abed3c17f0ca4c4ea36f",
    "critical": "6a86868a52e24aa3a03a449f",
    "high": "6a7c43dff635867f188841ba",
    "medium": "6a7c4398f635867f1888415e",
    "low": "6a7c4363f635867f18884115",
}

def _resolve_priority(priority: str | None) -> str | None:
    if not priority:
        return None
    clean = priority.strip()
    if re.fullmatch(r"[0-9a-fA-F]{24}", clean):
        return clean
    lower = clean.lower()
    for key, p_id in PRIORITY_MAP.items():
        if key in lower:
            return p_id
    return None

def _resolve_due_date(due_date: str | None) -> str | None:
    if not due_date:
        return None
    clean = due_date.strip().lower()
    now = datetime.now(timezone.utc)
    if clean == "today":
        return now.strftime("%Y-%m-%d")
    if clean == "tomorrow":
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    return due_date.strip()

async def _resolve_employee(identifier: str) -> tuple[str | None, str | None]:
    if not identifier:
        return None, None
    clean_id = identifier.strip()
    if re.fullmatch(r"[0-9a-fA-F]{24}", clean_id):
        return clean_id, None
    try:
        search_res = await employee_client.list_employees({"search": clean_id, "scope": "company"})
        data = search_res.get("data", []) if isinstance(search_res, dict) else []
        if not data:
            return None, None
        clean_lower = clean_id.lower()
        for emp in data:
            emp_id = emp.get("_id")
            p_info = emp.get("personalInfo") or {}
            full_name = p_info.get("legalFullName") or f"{p_info.get('firstName', '')} {p_info.get('lastName', '')}".strip()
            work_email = p_info.get("contact", {}).get("workEmail", "") if isinstance(p_info.get("contact"), dict) else ""
            emp_num = emp.get("employeeId", "")
            if clean_lower in full_name.lower() or clean_lower == work_email.lower() or clean_lower == emp_num.lower():
                return emp_id, full_name
        first_emp = data[0]
        p_info = first_emp.get("personalInfo") or {}
        first_name = p_info.get("legalFullName") or f"{p_info.get('firstName', '')} {p_info.get('lastName', '')}".strip()
        return first_emp.get("_id"), first_name
    except Exception:
        return None, None

@tool(description="Create a personal task with title and optional details", args_schema=CreateTaskArgs)
async def create_personal_task(
    title: str,
    description: str | None = None,
    taskType: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    dueDate: str | None = None,
) -> str:
    try:
        resolved_priority = _resolve_priority(priority)
        resolved_due_date = _resolve_due_date(dueDate)
        target_employee_id = None
        target_employee_name = None
        if assignee:
            target_employee_id, target_employee_name = await _resolve_employee(assignee)

        payload: dict[str, Any] = {
            "title": title,
            "isPersonal": True,
        }
        if description is not None:
            payload["description"] = {"message": description, "linkedAttachment": []} if isinstance(description, str) else description
        if taskType is not None:
            payload["taskType"] = taskType
        if resolved_priority:
            payload["priority"] = resolved_priority
        if status is not None:
            payload["status"] = status
        if resolved_due_date:
            payload["dueDate"] = resolved_due_date

        create_result = await task_client.create_task(payload)
        task_data = create_result.get("data", {}) if isinstance(create_result, dict) else {}
        task_mongo_id = task_data.get("_id")
        task_number = task_data.get("id")
        author_info = task_data.get("author") or {}
        author_id = author_info.get("_id")

        reassign_note = ""
        if target_employee_id and task_mongo_id:
            assignees_list = [target_employee_id]
            if author_id and author_id != target_employee_id:
                assignees_list.append(author_id)
            update_payload = {
                "assignee": target_employee_id,
                "assignees": assignees_list,
            }
            update_res = await task_client.update_single_task(task_mongo_id, update_payload)
            if isinstance(update_res, dict) and update_res.get("statusCode") == 200:
                reassign_note = f"Task successfully assigned to {target_employee_name or assignee}."
            else:
                reassign_note = f"Task created, but assigning to {assignee} returned: {update_res}."

        final_tasks = None
        if task_number:
            final_tasks = await task_client.list_tasks({"taskNumbers": task_number, "Scope": "PERSONAL"})

        if isinstance(final_tasks, dict) and final_tasks.get("data"):
            final_output = project_tool_output(final_tasks, "task")
        else:
            final_output = project_tool_output(create_result, "task")

        notes = []
        if priority and not resolved_priority:
            notes.append(f"Notice: Priority '{priority}' could not be matched to a system priority and was omitted.")
        elif priority and resolved_priority:
            notes.append(f"Notice: Priority '{priority}' was mapped to system priority.")
        if dueDate and resolved_due_date:
            notes.append(f"Notice: Due date set to {resolved_due_date}.")
        if reassign_note:
            notes.append(reassign_note)

        if notes:
            return f"{final_output}\n\nExecution Notes:\n" + "\n".join(f"- {n}" for n in notes)
        return final_output
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
    try:
        params: dict[str, Any] = {
            "Scope": Scope or "PERSONAL",
        }
        if taskNumbers:
            params["taskNumbers"] = ",".join(taskNumbers) if isinstance(taskNumbers, list) else str(taskNumbers)
        if assignees:
            resolved_assignees = []
            for a in (assignees if isinstance(assignees, list) else [assignees]):
                resolved_id, _ = await _resolve_employee(a)
                resolved_assignees.append(resolved_id or a)
            params["assignees"] = ",".join(resolved_assignees)
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
    try:
        payload: dict[str, Any] = {}
        notes = []
        if status is not None:
            payload["status"] = status
        if priority is not None:
            resolved_p = _resolve_priority(priority)
            if resolved_p:
                payload["priority"] = resolved_p
                notes.append(f"Priority '{priority}' mapped to system priority.")
            else:
                notes.append(f"Priority '{priority}' was invalid and not updated.")
        if assignee is not None:
            resolved_emp_id, resolved_name = await _resolve_employee(assignee)
            target_id = resolved_emp_id or assignee
            payload["assignee"] = target_id
            payload["assignees"] = [target_id]
            notes.append(f"Assignee updated to {resolved_name or assignee}.")
        if dueDate is not None:
            resolved_due = _resolve_due_date(dueDate)
            if resolved_due:
                payload["dueDate"] = resolved_due
                notes.append(f"Due date set to {resolved_due}.")
        result = await task_client.update_single_task(mongo_object_id, payload)
        output = project_tool_output(result, "task")
        if notes:
            return f"{output}\n\nExecution Notes:\n" + "\n".join(f"- {n}" for n in notes)
        return output
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Bulk update multiple tasks at once", args_schema=BulkUpdateTasksArgs)
async def bulk_update_tasks(
    ids: list[str],
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
) -> str:
    try:
        payload: dict[str, Any] = {"ids": ids}
        notes = []
        if status is not None:
            payload["status"] = status
        if priority is not None:
            resolved_p = _resolve_priority(priority)
            if resolved_p:
                payload["priority"] = resolved_p
                notes.append(f"Priority '{priority}' mapped to system priority.")
            else:
                notes.append(f"Priority '{priority}' was invalid and not updated.")
        if assignee is not None:
            resolved_emp_id, resolved_name = await _resolve_employee(assignee)
            target_id = resolved_emp_id or assignee
            payload["assignee"] = target_id
            payload["assignees"] = [target_id]
            notes.append(f"Assignee updated to {resolved_name or assignee}.")
        result = await task_client.bulk_update_tasks(payload)
        output = project_tool_output(result, "task")
        if notes:
            return f"{output}\n\nExecution Notes:\n" + "\n".join(f"- {n}" for n in notes)
        return output
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
