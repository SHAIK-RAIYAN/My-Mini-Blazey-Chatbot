from typing import Any
from pydantic import BaseModel, Field

class CreateEmployeeArgs(BaseModel):
    employmentType: str | None = Field(default="REGULAR", description="Employment type: REGULAR, CONTRACT, INTERN, or CONSULTANT")
    employmentBasisId: str | None = Field(default="6a761828514350d27df5b501", description="Unique ID of the employment basis")
    hireDate: str | None = Field(default=None, description="Hire date in ISO format (YYYY-MM-DD)")
    firstName: str = Field(..., description="First name of the employee")
    lastName: str = Field(..., description="Last name of the employee")
    workEmail: str = Field(..., description="Unique work email address of the employee")
    departmentId: str | None = Field(default="66425e9f8ab88ca5ceb01a84", description="Unique ID of the employee department")

class SearchEmployeesArgs(BaseModel):
    search: str | None = Field(default=None, description="Search keyword across names, emails, or IDs in the employee directory")
    employeeId: str | None = Field(default=None, description="Exact human-readable employee ID match (e.g. EMP-160, PSI-2784)")
    status: str | None = Field(default=None, description="Filter employees by status")
    employmentType: str | None = Field(default=None, description="Filter employees by employment type")
    departmentId: str | None = Field(default=None, description="Filter employees by department ID")
    scope: str | None = Field(default="company", description="Directory scope: company, team, joined, or left")
    limit: int | None = Field(default=20, description="Maximum number of employee records to return")

class GetEmployeeArgs(BaseModel):
    mongo_object_id: str = Field(..., description="Must be the 24-character hex MongoDB _id, NOT the human-readable employeeId")
    response_fields: str | None = Field(default=None, description="Comma-separated projection fields to return")

class UpdateEmployeeArgs(BaseModel):
    mongo_object_id: str = Field(..., description="Must be the 24-character hex MongoDB _id, NOT the human-readable employeeId")
    payload: dict[str, Any] = Field(..., description="Dictionary containing root fields to update on the employee")

class UpdatePersonalInfoArgs(BaseModel):
    mongo_object_id: str = Field(..., description="Must be the 24-character hex MongoDB _id, NOT the human-readable employeeId")
    payload: dict[str, Any] = Field(..., description="Dictionary containing personal information fields to update")
