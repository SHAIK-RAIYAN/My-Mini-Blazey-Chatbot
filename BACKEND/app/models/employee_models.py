from typing import Any
from pydantic import BaseModel, Field

class CreateEmployeeArgs(BaseModel):
    employmentType: str = Field(..., description="Employment type (e.g., Full-Time, Part-Time, Contractor)")
    employmentBasisId: str = Field(..., description="Unique ID of the employment basis")
    hireDate: str = Field(..., description="Hire date in ISO format (YYYY-MM-DD)")
    firstName: str = Field(..., description="First name of the employee")
    lastName: str = Field(..., description="Last name of the employee")
    workEmail: str = Field(..., description="Unique work email address of the employee")
    departmentId: str = Field(..., description="Unique ID of the employee department")

class SearchEmployeesArgs(BaseModel):
    search: str | None = Field(default=None, description="Search keyword across names, emails, or IDs")
    status: str | None = Field(default=None, description="Filter employees by status")
    employmentType: str | None = Field(default=None, description="Filter employees by employment type")
    departmentId: str | None = Field(default=None, description="Filter employees by department ID")
    limit: int | None = Field(default=20, description="Maximum number of employee records to return")

class GetEmployeeArgs(BaseModel):
    employee_id: str = Field(..., description="Unique ID of the employee")
    response_fields: str | None = Field(default=None, description="Comma-separated projection fields to return")

class UpdateEmployeeArgs(BaseModel):
    employee_id: str = Field(..., description="Unique ID of the employee to update")
    payload: dict[str, Any] = Field(..., description="Dictionary containing fields to update on the employee")
