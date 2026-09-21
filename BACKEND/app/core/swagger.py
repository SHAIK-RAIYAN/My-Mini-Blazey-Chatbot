from typing import Any

OPENAPI_TAGS: list[dict[str, Any]] = [
    {
        "name": "Agent",
        "description": "Agentic Chatbot operations including streaming interactions and human-in-the-loop (HITL) approval workflows.",
    },
    {
        "name": "System",
        "description": "Application diagnostic and service health monitoring endpoints.",
    },
]

SWAGGER_APP_CONFIG: dict[str, Any] = {
    "title": "Blazeup Agentic Orchestrator API",
    "description": "Agentic Chatbot backend interacting with Project and Employee microservices.",
    "version": "1.0.0",
    "docs_url": "/docs",
    "redoc_url": "/redoc",
    "openapi_tags": OPENAPI_TAGS,
}

CHAT_STREAM_DOCS: dict[str, Any] = {
    "summary": "Stream Agent Chat",
    "tags": ["Agent"],
    "description": "Accepts a thread ID and message, and returns an SSE stream detailing execution steps, tool invocations, and supervisor approval requests.",
    "response_description": "Server-Sent Events stream yielding JSON message updates and execution checkpoints.",
}

CHAT_APPROVE_DOCS: dict[str, Any] = {
    "summary": "Approve or Reject Pending Action",
    "tags": ["Agent"],
    "description": "Human-in-the-Loop (HITL) webhook endpoint. Evaluates supervisor approval for a pending mutating action. If approved, clears approval flags and streams the tool execution and final model response. If rejected, aborts the pending action and notifies the user.",
    "response_description": "Server-Sent Events stream yielding post-approval tool execution and final response.",
}

HEALTH_DOCS: dict[str, Any] = {
    "summary": "Service Health Check",
    "tags": ["System"],
    "description": "Returns current operational status and active deployment environment.",
    "response_description": "JSON object indicating service health status.",
}
