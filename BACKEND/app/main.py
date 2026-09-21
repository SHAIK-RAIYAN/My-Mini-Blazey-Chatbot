import json
from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, ToolMessage
from app.agent.graph import app_graph
from app.models.api_models import ChatRequest, ApprovalRequest
from app.db.mongo import get_database, close_client
from app.config import settings
from app.core.swagger import (
    SWAGGER_APP_CONFIG,
    CHAT_STREAM_DOCS,
    CHAT_APPROVE_DOCS,
    HEALTH_DOCS,
)

def format_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", str(item)))
            else:
                parts.append(str(item))
        return "".join(parts)
    if isinstance(content, dict):
        return content.get("text", str(content))
    return str(content) if content is not None else ""

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    db = get_database()
    try:
        await db.command("ping")
    except Exception:
        pass
    yield
    await close_client()

app = FastAPI(
    lifespan=lifespan,
    title=SWAGGER_APP_CONFIG["title"],
    description=SWAGGER_APP_CONFIG["description"],
    version=SWAGGER_APP_CONFIG["version"],
    docs_url=SWAGGER_APP_CONFIG["docs_url"],
    redoc_url=SWAGGER_APP_CONFIG["redoc_url"],
    openapi_tags=SWAGGER_APP_CONFIG.get("openapi_tags"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", **HEALTH_DOCS)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "env": settings.APP_ENV}

@app.post("/api/chat/stream", **CHAT_STREAM_DOCS)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    config = {"configurable": {"thread_id": request.thread_id}}
    input_data = {"messages": [HumanMessage(content=request.message)]}

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for step_chunk in app_graph.astream(input_data, config=config, stream_mode="updates"):
                for node_name, node_output in step_chunk.items():
                    chunk: dict[str, Any] = {"node": node_name}
                    messages = node_output.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
                        chunk["message"] = {
                            "type": getattr(last_msg, "type", "message"),
                            "content": format_content(getattr(last_msg, "content", "")),
                            "tool_calls": getattr(last_msg, "tool_calls", []),
                        }
                    if "requires_approval" in node_output:
                        chunk["requires_approval"] = node_output["requires_approval"]
                    if "pending_action" in node_output:
                        chunk["pending_action"] = node_output["pending_action"]
                    if "clarification_count" in node_output:
                        chunk["clarification_count"] = node_output["clarification_count"]

                    yield f"data: {json.dumps(chunk)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

@app.post("/api/chat/approve", **CHAT_APPROVE_DOCS)
async def chat_approve(request: ApprovalRequest) -> StreamingResponse:
    config = {"configurable": {"thread_id": request.thread_id}}
    current_state = await app_graph.aget_state(config)
    state_values = getattr(current_state, "values", {}) or {}

    pending_action = state_values.get("pending_action")
    if not pending_action:
        raise HTTPException(
            status_code=400,
            detail="No pending action requiring approval was found for the specified thread.",
        )

    async def approval_event_generator() -> AsyncGenerator[str, None]:
        try:
            if request.approved:
                await app_graph.aupdate_state(
                    config,
                    {"requires_approval": False},
                    as_node="check_hitl",
                )
                async for step_chunk in app_graph.astream(None, config=config, stream_mode="updates"):
                    for node_name, node_output in step_chunk.items():
                        chunk: dict[str, Any] = {"node": node_name}
                        messages = node_output.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            chunk["message"] = {
                                "type": getattr(last_msg, "type", "message"),
                                "content": format_content(getattr(last_msg, "content", "")),
                                "tool_calls": getattr(last_msg, "tool_calls", []),
                            }
                        if "requires_approval" in node_output:
                            chunk["requires_approval"] = node_output["requires_approval"]
                        if "pending_action" in node_output:
                            chunk["pending_action"] = node_output["pending_action"]
                        yield f"data: {json.dumps(chunk)}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            else:
                tool_name = pending_action.get("name", "operation")
                tool_id = pending_action.get("id", "")
                cancellation_message = ToolMessage(
                    content=f"The operation '{tool_name}' was rejected and aborted by the supervisor.",
                    name=tool_name,
                    tool_call_id=tool_id,
                )
                await app_graph.aupdate_state(
                    config,
                    {
                        "pending_action": None,
                        "requires_approval": False,
                        "messages": [cancellation_message],
                    },
                    as_node="execute_tools",
                )
                async for step_chunk in app_graph.astream(None, config=config, stream_mode="updates"):
                    for node_name, node_output in step_chunk.items():
                        chunk: dict[str, Any] = {"node": node_name}
                        messages = node_output.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            chunk["message"] = {
                                "type": getattr(last_msg, "type", "message"),
                                "content": format_content(getattr(last_msg, "content", "")),
                            }
                        yield f"data: {json.dumps(chunk)}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        approval_event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
