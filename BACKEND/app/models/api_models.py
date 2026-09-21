from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    thread_id: str = Field(
        ...,
        description="Unique thread identifier for conversation session",
        examples=["test-thread-123"],
        json_schema_extra={"example": "test-thread-123"},
    )
    message: str = Field(
        ...,
        description="User input message text",
        examples=["Change the status of task PROJ-1 to completed."],
        json_schema_extra={"example": "Change the status of task PROJ-1 to completed."},
    )

class ApprovalRequest(BaseModel):
    thread_id: str = Field(
        ...,
        description="Unique thread identifier for conversation session",
        examples=["test-thread-123"],
        json_schema_extra={"example": "test-thread-123"},
    )
    approved: bool = Field(
        ...,
        description="Approval decision boolean for pending action",
        examples=[True],
        json_schema_extra={"example": True},
    )
