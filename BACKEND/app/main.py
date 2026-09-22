import json
import re
import time
from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from app.agent.graph import app_graph
from app.models.api_models import ChatRequest
from app.db.mongo import get_database, close_client
from app.config import settings
from app.core.swagger import (
    SWAGGER_APP_CONFIG,
    CHAT_STREAM_DOCS,
    HEALTH_DOCS,
)

MONGO_ID_REGEX = re.compile(r"\b[0-9a-fA-F]{24}\b")
MONGO_TABLE_ROW_REGEX = re.compile(r"^\s*\|?\s*(?:MongoDB\s*ID|_id|Mongo\s*ID)\s*\|.*$\n?", re.MULTILINE | re.IGNORECASE)
MONGO_LABEL_REGEX = re.compile(r"(?:,\s*)?(?:\(?\s*MongoDB\s*(?:Object)?ID\s*:\s*[0-9a-fA-F]{24}\s*\)?)", re.IGNORECASE)

def hide_mongo_ids(text: str) -> str:
    """Strip or mask MongoDB ObjectIds and corresponding label text from assistant text."""
    if not text:
        return ""
    cleaned = MONGO_TABLE_ROW_REGEX.sub("", text)
    cleaned = MONGO_LABEL_REGEX.sub("", cleaned)
    cleaned = MONGO_ID_REGEX.sub("", cleaned)
    return cleaned

def format_content(content: Any) -> str:
    """Format diverse message content types into a unified text string."""
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
    """Manage application lifecycle for MongoDB connections and resources."""
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
    """Return application operational health and active environment name."""
    return {"status": "ok", "env": settings.APP_ENV}

@app.get("/api/chat/threads")
async def get_chat_threads() -> list[dict[str, str]]:
    """Retrieve distinct conversation threads sorted by recency with titles."""
    try:
        db = get_database()
        pipeline = [
            {"$group": {"_id": "$thread_id", "latest_checkpoint": {"$max": "$_id"}}},
            {"$sort": {"latest_checkpoint": -1}},
        ]
        cursor = db["checkpoints"].aggregate(pipeline)
        thread_ids = [
            doc["_id"]
            async for doc in cursor
            if doc.get("_id") and isinstance(doc["_id"], str) and doc["_id"].strip()
        ]
        result = []
        for thread_id in thread_ids:
            title = "New Chat"
            try:
                state = await app_graph.aget_state({"configurable": {"thread_id": thread_id}})
                state_values = getattr(state, "values", {}) or {}
                messages = state_values.get("messages", [])
                for msg in messages:
                    msg_type = getattr(msg, "type", "")
                    if msg_type in ("human", "user"):
                        content = format_content(getattr(msg, "content", "")).strip()
                        if content:
                            if len(content) > 35:
                                title = content[:35] + "..."
                            else:
                                title = content
                        break
            except Exception:
                pass
            result.append({"id": thread_id, "title": title})
        return result
    except Exception:
        return []

@app.get("/api/chat/history/{thread_id}")
async def get_chat_history(thread_id: str) -> dict[str, Any]:
    """Retrieve message history for a specific thread from MongoDB checkpoints."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await app_graph.aget_state(config)
        state_values = getattr(state, "values", {}) or {}
        raw_messages = state_values.get("messages", [])

        formatted_messages = []
        for idx, msg in enumerate(raw_messages):
            msg_type = getattr(msg, "type", "")
            if msg_type in ("human", "user"):
                role = "user"
            elif msg_type in ("ai", "assistant"):
                role = "assistant"
            elif msg_type == "tool":
                role = "tool"
            elif msg_type == "system":
                role = "system"
            else:
                role = "assistant"

            content = format_content(getattr(msg, "content", ""))
            if role == "assistant":
                content = hide_mongo_ids(content)

            tool_calls = getattr(msg, "tool_calls", []) or []

            item: dict[str, Any] = {
                "id": getattr(msg, "id", None) or f"hist-{idx}-{thread_id}",
                "role": role,
                "content": content,
                "name": getattr(msg, "name", ""),
                "timestamp": idx,
            }
            if tool_calls:
                item["toolCalls"] = tool_calls
            if role == "tool":
                item["node"] = "execute_tools"
            elif role == "assistant":
                item["node"] = "call_model"

            formatted_messages.append(item)

        return {"thread_id": thread_id, "messages": formatted_messages}
    except Exception as exc:
        return {"thread_id": thread_id, "messages": [], "error": str(exc)}

@app.post("/api/chat/stream", **CHAT_STREAM_DOCS)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream agent reasoning steps, tool executions, and responses using SSE."""
    config = {"configurable": {"thread_id": request.thread_id}}
    input_data = {"messages": [HumanMessage(content=request.message)]}

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate Server-Sent Events from agent execution stream."""
        try:
            async for step_chunk in app_graph.astream(input_data, config=config, stream_mode="updates"):
                for node_name, node_output in step_chunk.items():
                    chunk: dict[str, Any] = {"node": node_name}
                    messages = node_output.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
                        msg_type = getattr(last_msg, "type", "message")
                        content_str = format_content(getattr(last_msg, "content", ""))
                        if msg_type in ("ai", "assistant"):
                            content_str = hide_mongo_ids(content_str)
                        chunk["message"] = {
                            "id": getattr(last_msg, "id", None) or f"msg-{node_name}-{int(time.time() * 1000)}",
                            "type": msg_type,
                            "name": getattr(last_msg, "name", ""),
                            "content": content_str,
                            "tool_calls": getattr(last_msg, "tool_calls", []),
                        }
                    yield f"data: {json.dumps(chunk)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
