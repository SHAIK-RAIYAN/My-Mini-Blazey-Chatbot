from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    pending_action: dict[str, Any] | None
    requires_approval: bool
    clarification_count: int
