import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from langchain.tools import tool
from app.clients.project_client import ProjectClient
from app.clients.employee_client import EmployeeClient
from app.core.sanitizer import project_tool_output
from app.models.project_models import (
    CreateProjectArgs,
    ListProjectsArgs,
    GetProjectArgs,
    UpdateProjectArgs,
)

project_client = ProjectClient()
employee_client = EmployeeClient()

DEFAULT_PROJECT_MANAGER_ID = "6ab0d065ac2e1b78c2599b9d"

def _resolve_project_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    clean = date_str.strip().lower()
    now = datetime.now(timezone.utc)
    if clean == "today":
        return now.strftime("%Y-%m-%d")
    if clean == "tomorrow":
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if clean == "yesterday":
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "next week" in clean or "1 week" in clean or "a week" in clean:
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
    return date_str.strip()

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
            if clean_lower == full_name.lower() or clean_lower == work_email.lower() or clean_lower == emp_num.lower() or clean_lower in full_name.lower():
                return emp_id, full_name
        return None, None
    except Exception:
        return None, None

async def _resolve_project(identifier: str) -> tuple[str | None, str | None]:
    if not identifier:
        return None, None
    clean_id = identifier.strip()
    if re.fullmatch(r"[0-9a-fA-F]{24}", clean_id):
        return clean_id, None
    try:
        clean_lower = clean_id.lower()
        res = await project_client.list_projects({"search": clean_id, "limit": 50})
        data = res.get("data", []) if isinstance(res, dict) else []
        for p in data:
            p_id = p.get("_id")
            p_code = str(p.get("projectId") or "").lower()
            p_name = str(p.get("name") or "").lower()
            p_prefix = str(p.get("taskPrefix") or "").lower()
            if clean_lower in (p_code, p_prefix, p_name) or clean_lower in p_name:
                return p_id, p.get("name")
        all_res = await project_client.list_projects({"limit": 50})
        all_data = all_res.get("data", []) if isinstance(all_res, dict) else []
        for p in all_data:
            p_id = p.get("_id")
            p_code = str(p.get("projectId") or "").lower()
            p_name = str(p.get("name") or "").lower()
            p_prefix = str(p.get("taskPrefix") or "").lower()
            if clean_lower in (p_code, p_prefix, p_name) or clean_lower in p_name:
                return p_id, p.get("name")
        return None, None
    except Exception:
        return None, None

@tool(description="Create a new Project (NOT a task). Use this when the user asks to create, initiate, or start a new project.", args_schema=CreateProjectArgs)
async def create_project(
    name: str | None = None,
    title: str | None = None,
    startDate: str | None = "today",
    endDate: str | None = None,
    deadline: str | None = None,
    projectManager: str | None = None,
    description: str | None = None,
    priority: str | None = "Medium",
    status: str | None = "PLANNING",
    projectType: str | None = "INTERNAL",
    members: list[str] | None = None,
) -> str:
    try:
        project_name = (name or title or "").strip()
        if not project_name:
            return json.dumps({
                "status": "clarification_needed",
                "message": "A project name is required to create a project. Please ask the user what they would like to name the project.",
                "action": "create_project",
                "missing_parameters": ["name"]
            })

        target_end_raw = endDate or deadline
        if not target_end_raw:
            return json.dumps({
                "status": "clarification_needed",
                "message": "An end date or deadline is required to create a project. Please ask the user for the project completion date or duration.",
                "action": "create_project",
                "missing_parameters": ["endDate"]
            })

        resolved_start = _resolve_project_date(startDate or "today")
        resolved_end = _resolve_project_date(target_end_raw)

        pm_id = None
        pm_name = None
        if projectManager:
            pm_id, pm_name = await _resolve_employee(projectManager)
        if not pm_id:
            pm_id = DEFAULT_PROJECT_MANAGER_ID

        payload: dict[str, Any] = {
            "name": project_name,
            "startDate": resolved_start,
            "endDate": resolved_end,
            "projectManager": pm_id,
            "projectType": projectType or "INTERNAL",
            "status": status or "PLANNING",
            "priority": priority or "Medium",
        }
        if description:
            payload["description"] = description

        if members:
            resolved_members = []
            for m in members:
                m_id, _ = await _resolve_employee(m)
                if m_id:
                    resolved_members.append(m_id)
            if resolved_members:
                payload["members"] = resolved_members

        result = await project_client.create_project(payload)
        return project_tool_output(result, "project")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="List projects with optional search, status, and pagination filters", args_schema=ListProjectsArgs)
async def list_projects(
    search: str | None = None,
    projectId: str | None = None,
    status: str | None = None,
    page: int | None = 1,
    limit: int | None = 20,
) -> str:
    try:
        params: dict[str, Any] = {}
        if search:
            params["search"] = search
        if projectId:
            params["projectId"] = projectId
        if status:
            params["status"] = status
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        result = await project_client.list_projects(params)
        return project_tool_output(result, "project")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Get details of a specific project by ObjectId, project code, or name", args_schema=GetProjectArgs)
async def get_project(project_id: str) -> str:
    try:
        resolved_id, _ = await _resolve_project(project_id)
        target_id = resolved_id or project_id
        result = await project_client.get_project(target_id)
        return project_tool_output(result, "project")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Update an existing project details by ObjectId or project code", args_schema=UpdateProjectArgs)
async def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    projectManager: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
    members: list[str] | None = None,
) -> str:
    try:
        resolved_id, _ = await _resolve_project(project_id)
        target_id = resolved_id or project_id
        payload: dict[str, Any] = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if status:
            payload["status"] = status
        if priority:
            payload["priority"] = priority
        if startDate:
            payload["startDate"] = _resolve_project_date(startDate)
        if endDate:
            payload["endDate"] = _resolve_project_date(endDate)
        if projectManager:
            pm_id, _ = await _resolve_employee(projectManager)
            if pm_id:
                payload["projectManager"] = pm_id
        if members:
            resolved_members = []
            for m in members:
                m_id, _ = await _resolve_employee(m)
                if m_id:
                    resolved_members.append(m_id)
            if resolved_members:
                payload["members"] = resolved_members

        result = await project_client.update_project(target_id, payload)
        return project_tool_output(result, "project")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
