from pydantic import BaseModel, Field

class CreateProjectArgs(BaseModel):
    name: str | None = Field(default=None, description="Project name")
    title: str | None = Field(default=None, description="Alternative field for project title or name if user specifies 'title'")
    startDate: str | None = Field(default="today", description="Start date in YYYY-MM-DD or relative like 'today'. Defaults to today if only deadline or duration is provided.")
    endDate: str | None = Field(default=None, description="End date, deadline, or target duration in YYYY-MM-DD or relative like '1 month', 'next month', '2 weeks'")
    deadline: str | None = Field(default=None, description="Alternative field for project deadline or target duration if user specifies 'deadline'")
    projectManager: str | None = Field(default=None, description="Project manager employee name, email, or MongoDB ObjectId. If not specified, defaults to current user.")
    description: str | None = Field(default=None, description="Detailed project description")
    priority: str | None = Field(default="Medium", description="Priority level: Low, Medium, High, Critical")
    status: str | None = Field(default="PLANNING", description="Project status: PLANNING, READY, IN_PROGRESS, ON_HOLD, COMPLETED, CANCELLED")
    projectType: str | None = Field(default="INTERNAL", description="Type of project: INTERNAL or EXTERNAL")
    members: list[str] | None = Field(default=None, description="List of team member employee names, emails, or MongoDB ObjectIds")

class ListProjectsArgs(BaseModel):
    search: str | None = Field(default=None, description="Search term for project name or description")
    projectId: str | None = Field(default=None, description="Filter by project code, e.g. INTL-67")
    status: str | None = Field(default=None, description="Filter projects by status")
    page: int | None = Field(default=1, description="Page number for pagination")
    limit: int | None = Field(default=20, description="Maximum number of projects to return")

class GetProjectArgs(BaseModel):
    project_id: str = Field(..., description="Project 24-character hex MongoDB ObjectId, project code (e.g. INTL-67), or project name")

class UpdateProjectArgs(BaseModel):
    project_id: str = Field(..., description="Project 24-character hex MongoDB ObjectId or project code (e.g. INTL-67)")
    name: str | None = Field(default=None, description="New project name")
    description: str | None = Field(default=None, description="New project description")
    status: str | None = Field(default=None, description="New status: PLANNING, READY, IN_PROGRESS, ON_HOLD, COMPLETED, CANCELLED")
    priority: str | None = Field(default=None, description="New priority: Low, Medium, High, Critical")
    projectManager: str | None = Field(default=None, description="New project manager name, email, or MongoDB ObjectId")
    startDate: str | None = Field(default=None, description="New start date in YYYY-MM-DD format")
    endDate: str | None = Field(default=None, description="New end date in YYYY-MM-DD format")
    members: list[str] | None = Field(default=None, description="New list of member employee names, emails, or ObjectIds")
