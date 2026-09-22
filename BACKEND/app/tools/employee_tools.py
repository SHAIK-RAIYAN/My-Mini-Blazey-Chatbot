import json
from typing import Any
from langchain.tools import tool
from app.clients.employee_client import EmployeeClient
from app.core.sanitizer import project_tool_output
from app.models.employee_models import (
    CreateEmployeeArgs,
    SearchEmployeesArgs,
    GetEmployeeArgs,
    UpdateEmployeeArgs,
    UpdatePersonalInfoArgs,
)

employee_client = EmployeeClient()

@tool(description="Retrieve an employee profile by ID", args_schema=GetEmployeeArgs)
async def get_employee_profile(
    mongo_object_id: str,
    response_fields: str | None = None,
) -> str:
    """Retrieve an employee profile directly using their MongoDB ObjectId."""
    try:
        result = await employee_client.get_employee(
            employee_id=mongo_object_id.strip(),
            response_fields=response_fields,
        )
        return project_tool_output(result)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Search and list employees with optional filters", args_schema=SearchEmployeesArgs)
async def search_employees(
    search: str | None = None,
    employeeId: str | None = None,
    status: str | None = None,
    employmentType: str | None = None,
    departmentId: str | None = None,
    scope: str | None = "company",
    limit: int | None = 20,
) -> str:
    """Search employee directory using provided filter parameters."""
    try:
        params: dict[str, Any] = {"scope": scope or "company"}
        if search is not None:
            params["search"] = search
        if employeeId is not None:
            params["employeeId"] = employeeId
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
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Create a new employee record", args_schema=CreateEmployeeArgs)
async def create_employee(
    firstName: str,
    lastName: str,
    workEmail: str,
    employmentType: str | None = "REGULAR",
    employmentBasisId: str | None = "6a761828514350d27df5b501",
    hireDate: str | None = None,
    departmentId: str | None = "66425e9f8ab88ca5ceb01a84",
) -> str:
    """Create a new employee record in the directory."""
    try:
        payload: dict[str, Any] = {
            "employmentType": employmentType or "REGULAR",
            "employmentBasis": {"_id": employmentBasisId or "6a761828514350d27df5b501", "name": "Full Time"},
            "hireDate": hireDate or "2026-10-01",
            "personalInfo": {
                "firstName": firstName,
                "lastName": lastName,
                "dob": "1995-01-01",
                "gender": "PREFER_NOT_TO_SAY",
                "contact": {"workEmail": workEmail},
                "emergencyContacts": [
                    {
                        "name": "Primary Contact",
                        "relationship": "OTHER",
                        "isPrimary": True,
                        "phone": {"countryCode": "+1", "number": "0000000000"},
                    }
                ],
            },
            "employmentDetail": {
                "department": {"_id": departmentId or "66425e9f8ab88ca5ceb01a84"},
            },
        }
        result = await employee_client.create_employee(payload)
        return project_tool_output(result)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Update root fields on an employee record by ID", args_schema=UpdateEmployeeArgs)
async def update_employee_record(
    mongo_object_id: str,
    payload: dict[str, Any],
) -> str:
    """Update root organizational fields on an employee record."""
    try:
        result = await employee_client.update_employee(employee_id=mongo_object_id, payload=payload)
        return project_tool_output(result)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Update personal information on an employee record by ID", args_schema=UpdatePersonalInfoArgs)
async def update_employee_personal_info(
    mongo_object_id: str,
    payload: dict[str, Any],
) -> str:
    """Update personal information fields on an employee record."""
    try:
        result = await employee_client.update_personal_info(employee_id=mongo_object_id, payload=payload)
        return project_tool_output(result)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
