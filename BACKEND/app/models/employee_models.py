from typing import Any
from pydantic import BaseModel, Field

class CreateEmployeeArgs(BaseModel):
    firstName: str = Field(..., description="First name of the employee")
    lastName: str = Field(..., description="Last name of the employee")
    workEmail: str = Field(..., description="Unique work email address of the employee")
    jobTitle: str | None = Field(default="Software Engineer", description="Job title or role of the employee")
    employmentType: str | None = Field(default="REGULAR", description="Employment type: REGULAR, CONTRACT, INTERN, or CONSULTANT")
    hireDate: str | None = Field(default=None, description="Hire date in ISO format (YYYY-MM-DD)")

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

class UpdateJobTitleArgs(BaseModel):
    mongo_object_id: str = Field(..., description="Must be the 24-character hex MongoDB _id of the employee, NOT the human-readable employeeId")
    job_title: str = Field(..., description="New job title / role name (e.g. 'AI Engineer', 'Senior Software Engineer')")
    reason: str | None = Field(default=None, description="Reason for the role or title change")
