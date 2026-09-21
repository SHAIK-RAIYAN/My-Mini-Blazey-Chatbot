import json
from typing import Any
from langchain.tools import tool
from app.clients.employee_client import EmployeeClient
from app.models.employee_models import (
    CreateEmployeeArgs,
    SearchEmployeesArgs,
    GetEmployeeArgs,
    UpdateEmployeeArgs,
)

employee_client = EmployeeClient()

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

@tool(description="Retrieve an employee profile by ID", args_schema=GetEmployeeArgs)
async def get_employee_profile(
    employee_id: str,
    response_fields: str | None = None,
) -> str:
    result = await employee_client.get_employee(
        employee_id=employee_id,
        response_fields=response_fields,
    )
    return project_tool_output(result)

@tool(description="Search and list employees with optional filters", args_schema=SearchEmployeesArgs)
async def search_employees(
    search: str | None = None,
    status: str | None = None,
    employmentType: str | None = None,
    departmentId: str | None = None,
    limit: int | None = 20,
) -> str:
    params: dict[str, Any] = {}
    if search is not None:
        params["search"] = search
    if status is not None:
        params["status"] = status
    if employmentType is not None:
        params["employmentType"] = employmentType
    if departmentId is not None:
        params["departmentId"] = departmentId
    if limit is not None:
        params["limit"] = limit
    result = await employee_client.list_employees(params=params)
    return project_tool_output(result)

@tool(description="Create a new employee record", args_schema=CreateEmployeeArgs)
async def create_employee(
    employmentType: str,
    employmentBasisId: str,
    hireDate: str,
    firstName: str,
    lastName: str,
    workEmail: str,
    departmentId: str,
) -> str:
    payload: dict[str, Any] = {
        "employmentType": employmentType,
        "employmentBasisId": employmentBasisId,
        "employmentBasis": {"_id": employmentBasisId},
        "hireDate": hireDate,
        "firstName": firstName,
        "lastName": lastName,
        "workEmail": workEmail,
        "departmentId": departmentId,
        "personalInfo": {
            "firstName": firstName,
            "lastName": lastName,
            "contact": {"workEmail": workEmail},
            "emergencyContacts": [
                {
                    "name": "Primary Contact",
                    "relationship": "Other",
                    "phone": {"number": "0000000000"},
                    "isPrimary": True,
                }
            ],
        },
        "employmentDetail": {
            "department": {"_id": departmentId},
        },
    }
    result = await employee_client.create_employee(payload)
    return project_tool_output(result)

@tool(description="Update an employee record by ID", args_schema=UpdateEmployeeArgs)
async def update_employee_record(
    employee_id: str,
    payload: dict[str, Any],
) -> str:
    result = await employee_client.update_employee(employee_id=employee_id, payload=payload)
    return project_tool_output(result)
