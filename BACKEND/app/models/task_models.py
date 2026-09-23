from pydantic import BaseModel, Field

class CreateTaskArgs(BaseModel):
    title: str = Field(..., description="Title of the task")
    description: str | None = Field(default=None, description="Detailed description of the task")
    taskType: str | None = Field(default=None, description="Type or category of the task (e.g. Task, Story, Bug, Feature, Epic)")
    project: str | None = Field(default=None, description="Target Project MongoDB ObjectId, project code (e.g. INTL-68), or project name. Required for all project tasks.")
    isPersonal: bool | None = Field(default=None, description="Set to True ONLY if the user explicitly requests a personal task. Never set to True on your own.")
    assignee: str | None = Field(default=None, description="Assignee employee name, email, or 24-character hex MongoDB ObjectId")
    priority: str | None = Field(default=None, description="Priority level name (e.g., urgent, High, Medium, Low, Critical) or MongoDB ObjectId")
    status: str | None = Field(default=None, description="Initial status of the task")
    startDate: str | None = Field(default=None, description="Task start date in ISO format YYYY-MM-DD or relative like 'today'")
    dueDate: str | None = Field(default=None, description="Due date in ISO format YYYY-MM-DD or relative like 'tomorrow', 'next week'")

class ListTasksArgs(BaseModel):
    taskNumbers: list[str] | None = Field(default=None, description="List of task numbers to filter by")
    project: str | None = Field(default=None, description="Project MongoDB ObjectId, project code (e.g. INTL-68), or project name to filter project tasks")
    assignees: list[str] | None = Field(default=None, description="List of assignee IDs or emails to filter by")
    Scope: str | None = Field(default=None, description="Task scope: 'PROJECT' for project tasks, 'PERSONAL' for personal tasks, 'EMPLOYEE' for my tasks")
    page: int | None = Field(default=1, description="Page number for pagination")
    limit: int | None = Field(default=20, description="Maximum number of tasks to return")
    status: str | None = Field(default=None, description="Filter tasks by status")

class UpdateTaskArgs(BaseModel):
    mongo_object_id: str = Field(..., description="The task identifier to update. Accepts either a human-readable task number (e.g., 'PERS-38', 'BLAZ6-1') or a 24-character hex MongoDB _id.")
    title: str | None = Field(default=None, description="New title for the task")
    description: str | None = Field(default=None, description="New description for the task")
    status: str | None = Field(default=None, description="New status for the task (e.g. New, inprogress, Completed, done, Blocked)")
    priority: str | None = Field(default=None, description="New priority name (e.g., urgent, High, Medium, Low, Critical) or MongoDB ObjectId")
    assignee: str | None = Field(default=None, description="New assignee employee name, email, or 24-character hex MongoDB ObjectId")
    startDate: str | None = Field(default=None, description="Task start date in YYYY-MM-DD format. Required before completing a task.")
    dueDate: str | None = Field(default=None, description="New due date in ISO format YYYY-MM-DD or ISO 8601 string")
    endDate: str | None = Field(default=None, description="Task end date in YYYY-MM-DD format")

class BulkUpdateTasksArgs(BaseModel):
    ids: list[str] = Field(..., description="Must be a list of 24-character hex MongoDB _ids, NOT human-readable taskNumbers")
    status: str | None = Field(default=None, description="New status for the tasks")
    priority: str | None = Field(default=None, description="New priority name or MongoDB ObjectId")
    assignee: str | None = Field(default=None, description="New assignee name, email, or MongoDB ObjectId")
    startDate: str | None = Field(default=None, description="Start date in YYYY-MM-DD format for tasks")
    endDate: str | None = Field(default=None, description="End date in YYYY-MM-DD format for tasks")
