from pydantic import BaseModel, Field

class CreateTaskArgs(BaseModel):
    title: str = Field(..., description="Title of the task")
    description: str | None = Field(default=None, description="Detailed description of the task")
    taskType: str | None = Field(default=None, description="Type or category of the task")
    assignee: str | None = Field(default=None, description="Assignee email or user ID")
    priority: str | None = Field(default=None, description="Priority level of the task")
    status: str | None = Field(default=None, description="Initial status of the task")

class ListTasksArgs(BaseModel):
    taskNumbers: list[str] | None = Field(default=None, description="List of task numbers to filter by")
    assignees: list[str] | None = Field(default=None, description="List of assignee IDs or emails to filter by")
    Scope: str | None = Field(default="PERSONAL", description="Task scope: PERSONAL, EMPLOYEE, or PROJECT")
    page: int | None = Field(default=1, description="Page number for pagination")
    limit: int | None = Field(default=20, description="Maximum number of tasks to return")
    status: str | None = Field(default=None, description="Filter tasks by status")

class UpdateTaskArgs(BaseModel):
    mongo_object_id: str = Field(..., description="Must be the 24-character hex MongoDB _id, NOT the human-readable taskNumber or id")
    status: str | None = Field(default=None, description="New status for the task")
    priority: str | None = Field(default=None, description="New priority level for the task")
    assignee: str | None = Field(default=None, description="New assignee ID or email")
    dueDate: str | None = Field(default=None, description="New due date in ISO format")

class BulkUpdateTasksArgs(BaseModel):
    ids: list[str] = Field(..., description="Must be a list of 24-character hex MongoDB _ids, NOT human-readable taskNumbers")
    status: str | None = Field(default=None, description="New status for the tasks")
    priority: str | None = Field(default=None, description="New priority level for the tasks")
    assignee: str | None = Field(default=None, description="New assignee for the tasks")
