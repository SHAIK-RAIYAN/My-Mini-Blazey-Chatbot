from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """Schema representing the shared execution state across agent graph nodes."""
    messages: Annotated[list[Any], add_messages]
    clarification_count: int
    loop_count: int
