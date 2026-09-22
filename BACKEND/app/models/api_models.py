from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Payload schema for streaming chat interaction requests."""
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
