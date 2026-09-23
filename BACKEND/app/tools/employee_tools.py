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
    UpdateJobTitleArgs,
)

employee_client = EmployeeClient()

@tool(description="Retrieve an employee profile by ID", args_schema=GetEmployeeArgs)
async def get_employee_profile(
    mongo_object_id: str,
    response_fields: str | None = None,
) -> str:
    try:
        result = await employee_client.get_employee(
            employee_id=mongo_object_id.strip(),
            response_fields=response_fields,
        )
        return project_tool_output(result, "employee")
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
        return project_tool_output(result, "employee")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Create a new employee record", args_schema=CreateEmployeeArgs)
async def create_employee(
    firstName: str,
    lastName: str,
    workEmail: str,
    jobTitle: str | None = "Software Engineer",
    employmentType: str | None = "REGULAR",
    hireDate: str | None = None,
) -> str:
    try:
        clean_email = workEmail.strip()
        payload: dict[str, Any] = {
            "employmentType": employmentType or "REGULAR",
            "employmentBasis": {"_id": "6a761828514350d27df5b501", "name": "Full Time"},
            "hireDate": hireDate or "2026-10-01",
            "personalInfo": {
                "firstName": firstName.strip(),
                "lastName": lastName.strip(),
                "dob": "1995-01-01",
                "gender": "PREFER_NOT_TO_SAY",
                "contact": {"workEmail": clean_email},
                "address": {
                    "country": "India",
                    "state": "Karnataka",
                    "city": "Bangalore",
                    "pinCode": "560100",
                    "addressLine1": "Tech Park Road",
                },
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
                "legalEntity": {"_id": "6a78591df14cec0c9d6156f4", "name": "Blazeup India"},
                "department": {
                    "_id": "6a7621c9514350d27df5c044",
                    "name": "Engineering",
                    "departmentId": "3",
                },
                "jobTitle": {"name": jobTitle or "Software Engineer"},
                "campus": {
                    "_id": "6a7aaed46ea967e1343db1ee",
                    "name": "Bangalore Tech Park",
                },
                "workMode": "REMOTE",
            },
        }
        result = await employee_client.create_employee(payload)
        return project_tool_output(result, "employee")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Update an employee's job title or role in the organization", args_schema=UpdateJobTitleArgs)
async def update_employee_job_title(
    mongo_object_id: str,
    job_title: str,
    reason: str | None = None,
) -> str:
    try:
        movement_payload = {
            "employeeId": mongo_object_id.strip(),
            "movementType": "ROLE_CHANGE",
            "kind": "CORRECTION",
            "to": {
                "role": {"name": job_title.strip()}
            },
            "reason": reason or f"Job title updated to {job_title.strip()}"
        }
        await employee_client.create_movement(movement_payload)
        emp_res = await employee_client.get_employee(mongo_object_id.strip())
        return project_tool_output(emp_res, "employee")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Update root fields on an employee record by ID", args_schema=UpdateEmployeeArgs)
async def update_employee_record(
    mongo_object_id: str,
    payload: dict[str, Any],
) -> str:
    try:
        clean_payload = dict(payload)
        role_val = None
        for key in ("jobTitle", "job_title", "designation", "role"):
            if key in clean_payload:
                val = clean_payload.pop(key)
                if isinstance(val, dict):
                    role_val = val.get("name") or val.get("role")
                elif isinstance(val, str):
                    role_val = val

        ed = clean_payload.get("employmentDetail") or clean_payload.get("employmentDetails")
        if isinstance(ed, dict):
            for key in ("jobTitle", "job_title", "designation", "role"):
                if key in ed:
                    val = ed.pop(key)
                    if isinstance(val, dict):
                        role_val = val.get("name") or val.get("role")
                    elif isinstance(val, str):
                        role_val = val

        if role_val:
            await employee_client.create_movement({
                "employeeId": mongo_object_id.strip(),
                "movementType": "ROLE_CHANGE",
                "kind": "CORRECTION",
                "to": {"role": {"name": role_val.strip()}},
                "reason": f"Role updated to {role_val.strip()}"
            })

        if clean_payload:
            result = await employee_client.update_employee(employee_id=mongo_object_id, payload=clean_payload)
        else:
            result = await employee_client.get_employee(mongo_object_id.strip())
        return project_tool_output(result, "employee")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@tool(description="Update personal information on an employee record by ID", args_schema=UpdatePersonalInfoArgs)
async def update_employee_personal_info(
    mongo_object_id: str,
    payload: dict[str, Any],
) -> str:
    try:
        result = await employee_client.update_personal_info(employee_id=mongo_object_id, payload=payload)
        return project_tool_output(result, "employee")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
