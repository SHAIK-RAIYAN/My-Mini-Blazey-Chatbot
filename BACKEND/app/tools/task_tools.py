import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from langchain.tools import tool
from app.clients.task_client import TaskClient
from app.clients.employee_client import EmployeeClient
from app.tools.project_tools import _resolve_project
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

STATUS_MAP = {
    "new": "6a7c444ef635867f18884241",
    "inprogress": "6a7c4861f635867f188846fb",
    "in progress": "6a7c4861f635867f188846fb",
    "in-progress": "6a7c4861f635867f188846fb",
    "doing": "6a7c4861f635867f188846fb",
    "pending": "6a7eded995964a5ef177db4a",
    "completed": "6a7c45b7f635867f188843ec",
    "complete": "6a7c45b7f635867f188843ec",
    "done": "6a7c45b7f635867f188843ec",
    "finished": "6a7c45b7f635867f188843ec",
    "blocked": "6a82ad0bac096c936ac74430",
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

def _resolve_status(status: str | None) -> str | None:
    if not status:
        return None
    clean = status.strip()
    if re.fullmatch(r"[0-9a-fA-F]{24}", clean):
        return clean
    lower = clean.lower()
    for key, s_id in STATUS_MAP.items():
        if key in lower:
            return s_id
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
    if clean == "yesterday":
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "next week" in clean or "in 1 week" in clean or "in a week" in clean:
        return (now + timedelta(days=7)).strftime("%Y-%m-%d")
    if "next month" in clean or "1 month" in clean or "a month" in clean or "one month" in clean:
        return (now + timedelta(days=30)).strftime("%Y-%m-%d")
    if "2 months" in clean or "two months" in clean:
        return (now + timedelta(days=60)).strftime("%Y-%m-%d")
    if "3 months" in clean or "three months" in clean:
        return (now + timedelta(days=90)).strftime("%Y-%m-%d")
    if "end of month" in clean:
        next_month = now.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        return last_day.strftime("%Y-%m-%d")
    if "end of year" in clean:
        return f"{now.year}-12-31"
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
        exact_matches = []
        partial_matches = []
        for emp in data:
            emp_id = emp.get("_id")
            p_info = emp.get("personalInfo") or {}
            full_name = p_info.get("legalFullName") or f"{p_info.get('firstName', '')} {p_info.get('lastName', '')}".strip()
            work_email = p_info.get("contact", {}).get("workEmail", "") if isinstance(p_info.get("contact"), dict) else ""
            emp_num = emp.get("employeeId", "")
            if clean_lower == full_name.lower() or clean_lower == work_email.lower() or clean_lower == emp_num.lower():
                exact_matches.append((emp_id, full_name))
            elif clean_lower in full_name.lower() or clean_lower in work_email.lower():
                partial_matches.append((emp_id, full_name))
        if len(exact_matches) == 1:
            return exact_matches[0]
        if not exact_matches and len(partial_matches) == 1:
            return partial_matches[0]
        return None, None
    except Exception:
        return None, None

@tool(description="Create a task within a target project, or an explicit personal task (NOT for creating projects)", args_schema=CreateTaskArgs)
async def create_task(
    title: str,
    project: str | None = None,
    isPersonal: bool | None = None,
    description: str | None = None,
    taskType: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    startDate: str | None = None,
    dueDate: str | None = None,
) -> str:
    try:
        resolved_priority = _resolve_priority(priority)
        resolved_due_date = _resolve_due_date(dueDate)
        resolved_start_date = _resolve_due_date(startDate)
        resolved_status = _resolve_status(status)

        target_employee_id = None
        target_employee_name = None
        if assignee:
            target_employee_id, target_employee_name = await _resolve_employee(assignee)

        target_project_id = None
        target_project_name = None
        if project:
            target_project_id, target_project_name = await _resolve_project(project)
            if not target_project_id and isPersonal is not True:
                return json.dumps({
                    "status": "project_not_found",
                    "message": f"Project '{project}' was not found in your workspace. Please verify the project name or ask the user whether they would like to create this project.",
                    "action": "create_task",
                })

        if isPersonal is True:
            is_personal_task = True
        elif target_project_id:
            is_personal_task = False
        else:
            return json.dumps({
                "status": "clarification_needed",
                "message": "A target project is required to create a task. Please ask the user which project they want to add this task to, or whether they explicitly want a personal task.",
                "action": "create_task",
                "missing_parameters": ["project"]
            })

        if not is_personal_task and target_project_id:
            payload: dict[str, Any] = {
                "title": title,
                "isPersonal": False,
                "project": target_project_id,
                "type": taskType or "Task",
                "status": resolved_status or "6a7c444ef635867f18884241",
                "priority": resolved_priority or "6a7c4398f635867f1888415e",
            }
            if description is not None:
                payload["description"] = {"message": description, "linkedAttachment": []} if isinstance(description, str) else description
            if resolved_start_date:
                payload["startDate"] = resolved_start_date
            if resolved_due_date:
                payload["dueDate"] = resolved_due_date
            if target_employee_id:
                payload["assignee"] = target_employee_id
                payload["assignees"] = [target_employee_id]

            create_result = await task_client.create_task(payload)
            task_data = create_result.get("data", {}) if isinstance(create_result, dict) else {}
            task_number = task_data.get("id")

            final_tasks = None
            if task_number and target_project_id:
                final_tasks = await task_client.list_tasks({
                    "taskNumbers": task_number,
                    "projectIds": target_project_id,
                    "Scope": "PROJECT",
                })

            if isinstance(final_tasks, dict) and final_tasks.get("data"):
                final_output = project_tool_output(final_tasks, "task")
            else:
                final_output = project_tool_output(create_result, "task")

            notes = []
            if target_project_name:
                notes.append(f"Task created inside project '{target_project_name}'.")
            if priority and not resolved_priority:
                notes.append(f"Notice: Priority '{priority}' could not be matched to a system priority and was omitted.")
            elif priority and resolved_priority:
                notes.append(f"Notice: Priority '{priority}' was mapped to system priority.")
            if startDate and resolved_start_date:
                notes.append(f"Notice: Start date set to {resolved_start_date}.")
            if dueDate and resolved_due_date:
                notes.append(f"Notice: Due date set to {resolved_due_date}.")

            if notes:
                return f"{final_output}\n\nExecution Notes:\n" + "\n".join(f"- {n}" for n in notes)
            return final_output

        payload = {
            "title": title,
            "isPersonal": True,
            "type": taskType or "Task",
        }
        if description is not None:
            payload["description"] = {"message": description, "linkedAttachment": []} if isinstance(description, str) else description
        if resolved_start_date:
            payload["startDate"] = resolved_start_date
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
        if startDate and resolved_start_date:
            notes.append(f"Notice: Start date set to {resolved_start_date}.")
        if dueDate and resolved_due_date:
            notes.append(f"Notice: Due date set to {resolved_due_date}.")
        if reassign_note:
            notes.append(reassign_note)

        if notes:
            return f"{final_output}\n\nExecution Notes:\n" + "\n".join(f"- {n}" for n in notes)
        return final_output
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="List tasks with optional filters by project, task numbers, or assignees", args_schema=ListTasksArgs)
async def list_tasks(
    taskNumbers: list[str] | None = None,
    project: str | None = None,
    assignees: list[str] | None = None,
    Scope: str | None = "PERSONAL",
    page: int | None = 1,
    limit: int | None = 20,
    status: str | None = None,
) -> str:
    try:
        target_scope = Scope or "PERSONAL"
        params: dict[str, Any] = {}
        if project:
            proj_id, _ = await _resolve_project(project)
            if proj_id:
                params["projectIds"] = proj_id
                target_scope = "PROJECT"
        params["Scope"] = target_scope
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
            resolved_s = _resolve_status(status)
            params["status"] = resolved_s or status
        result = await task_client.list_tasks(params)
        return project_tool_output(result, "task")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Update a single task by ID", args_schema=UpdateTaskArgs)
async def update_task_by_id(
    mongo_object_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    startDate: str | None = None,
    dueDate: str | None = None,
    endDate: str | None = None,
) -> str:
    try:
        clean_target_id = mongo_object_id.strip()
        target_mongo_id = clean_target_id
        if not re.fullmatch(r"[0-9a-fA-F]{24}", clean_target_id):
            lookup_res = await task_client.list_tasks({"taskNumbers": clean_target_id, "Scope": "PERSONAL"})
            data = lookup_res.get("data", []) if isinstance(lookup_res, dict) else []
            if not data:
                lookup_res = await task_client.list_tasks({"taskNumbers": clean_target_id, "Scope": "EMPLOYEE"})
                data = lookup_res.get("data", []) if isinstance(lookup_res, dict) else []
            if not data:
                lookup_res = await task_client.list_tasks({"taskNumbers": clean_target_id, "Scope": "PROJECT"})
                data = lookup_res.get("data", []) if isinstance(lookup_res, dict) else []
            if data and data[0].get("_id"):
                target_mongo_id = str(data[0]["_id"])
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Could not find task with identifier '{mongo_object_id}'. Please verify the Task ID."
                })

        payload: dict[str, Any] = {}
        notes = []
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = {"message": description, "linkedAttachment": []} if isinstance(description, str) else description
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
        if startDate is not None:
            resolved_start = _resolve_due_date(startDate)
            if resolved_start:
                payload["startDate"] = resolved_start
                notes.append(f"Start date set to {resolved_start}.")
        if dueDate is not None:
            resolved_due = _resolve_due_date(dueDate)
            if resolved_due:
                payload["dueDate"] = resolved_due
                notes.append(f"Due date set to {resolved_due}.")
        if endDate is not None:
            resolved_end = _resolve_due_date(endDate)
            if resolved_end:
                payload["endDate"] = resolved_end
                notes.append(f"End date set to {resolved_end}.")

        resolved_s = None
        if status is not None:
            resolved_s = _resolve_status(status)
            if not resolved_s and re.fullmatch(r"[0-9a-fA-F]{24}", status.strip()):
                resolved_s = status.strip()
            if resolved_s:
                payload["status"] = resolved_s
                notes.append(f"Status '{status}' mapped to system status.")
            else:
                notes.append(f"Status '{status}' could not be mapped.")

        is_completing = resolved_s == "6a7c45b7f635867f188843ec"

        if is_completing:
            start_date_val = payload.pop("startDate", None)
            if not start_date_val:
                start_date_val = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await task_client.update_single_task(target_mongo_id, {"startDate": start_date_val})
            notes.append(f"Task start date ensured as {start_date_val} before completion.")

        result = await task_client.update_single_task(target_mongo_id, payload)
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
    startDate: str | None = None,
    endDate: str | None = None,
) -> str:
    try:
        payload: dict[str, Any] = {"ids": ids}
        notes = []
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
        if startDate is not None:
            resolved_start = _resolve_due_date(startDate)
            if resolved_start:
                payload["startDate"] = resolved_start
        if endDate is not None:
            resolved_end = _resolve_due_date(endDate)
            if resolved_end:
                payload["endDate"] = resolved_end

        resolved_s = None
        if status is not None:
            resolved_s = _resolve_status(status)
            if not resolved_s and re.fullmatch(r"[0-9a-fA-F]{24}", status.strip()):
                resolved_s = status.strip()
            if resolved_s:
                payload["status"] = resolved_s
                notes.append(f"Status '{status}' mapped to system status.")

        is_completing = resolved_s == "6a7c45b7f635867f188843ec"
        if is_completing:
            start_date_val = payload.pop("startDate", None)
            if not start_date_val:
                start_date_val = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await task_client.bulk_update_tasks({"ids": ids, "startDate": start_date_val})
            notes.append(f"Task start date ensured as {start_date_val} before completion.")

        result = await task_client.bulk_update_tasks(payload)
        output = project_tool_output(result, "task")
        if notes:
            return f"{output}\n\nExecution Notes:\n" + "\n".join(f"- {n}" for n in notes)
        return output
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
