from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState
from app.agent.nodes import (
    call_model,
    should_continue,
    check_hitl,
    route_hitl,
    execute_tools,
)
from app.db.mongo import get_database, AsyncMongoDBSaver

workflow = StateGraph(AgentState)

workflow.add_node("call_model", call_model)
workflow.add_node("check_hitl", check_hitl)
workflow.add_node("execute_tools", execute_tools)

workflow.add_edge(START, "call_model")

workflow.add_conditional_edges(
    "call_model",
    should_continue,
    {
        "tools": "check_hitl",
        "end": END,
    },
)

workflow.add_conditional_edges(
    "check_hitl",
    route_hitl,
    {
        "pause": END,
        "continue": "execute_tools",
    },
)

workflow.add_edge("execute_tools", "call_model")

db = get_database()
checkpointer = AsyncMongoDBSaver(database=db)
app_graph = workflow.compile(checkpointer=checkpointer)
graph = app_graph
