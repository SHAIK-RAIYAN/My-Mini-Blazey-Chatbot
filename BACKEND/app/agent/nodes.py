import asyncio
import json
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from app.config import settings
from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_PROMPT
from app.core.logger import get_logger
from app.tools import (
    create_project,
    list_projects,
    get_project,
    update_project,
    create_task,
    list_tasks,
    update_task_by_id,
    bulk_update_tasks,
    get_employee_profile,
    search_employees,
    create_employee,
    update_employee_job_title,
    update_employee_record,
    update_employee_personal_info,
)

logger = get_logger()

tools = [
    create_project,
    list_projects,
    get_project,
    update_project,
    create_task,
    list_tasks,
    update_task_by_id,
    bulk_update_tasks,
    get_employee_profile,
    search_employees,
    create_employee,
    update_employee_job_title,
    update_employee_record,
    update_employee_personal_info,
]
tool_map = {tool.name: tool for tool in tools}

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=settings.GOOGLE_API_KEY if settings.GOOGLE_API_KEY else "AIzaSyDummyKeyForInitializationPlaceholder",
)
model_with_tools = llm.bind_tools(tools)

try:
    from google.api_core.exceptions import ResourceExhausted
except Exception:
    class ResourceExhausted(Exception):
        pass

def is_rate_limit_error(exc: BaseException) -> bool:
    if isinstance(exc, ResourceExhausted):
        return True
    err_str = str(exc).lower()
    return "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=5, max=30),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True,
)
async def invoke_model_with_retry(messages: list[Any]) -> Any:
    return await model_with_tools.ainvoke(messages)

async def call_model(state: AgentState) -> dict[str, Any]:
    await asyncio.sleep(2)
    messages = state.get("messages", [])
    prompt_messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT)]
    for message in messages:
        if not isinstance(message, SystemMessage):
            prompt_messages.append(message)

    try:
        response = await invoke_model_with_retry(prompt_messages)
    except Exception as exc:
        if is_rate_limit_error(exc):
            fallback_message = AIMessage(
                content="Agent execution paused due to API quota limits. Please wait 30 seconds before submitting another request."
            )
            return {
                "messages": [fallback_message],
                "clarification_count": state.get("clarification_count", 0),
                "loop_count": state.get("loop_count", 0),
            }
        raise

    if getattr(response, "tool_calls", None):
        for t in response.tool_calls:
            args_str = json.dumps(t.get("args", {}))
            logger.info(f"\nTool Dispatched: {t['name']} | Args: {args_str}\n")

    clarification_count = state.get("clarification_count", 0)

    has_tool_calls = bool(getattr(response, "tool_calls", None))
    content_str = response.content if isinstance(response.content, str) else str(response.content or "")
    is_question = "?" in content_str or any(
        phrase in content_str.lower()
        for phrase in ["could you", "can you", "please specify", "please provide", "clarify"]
    )

    if not has_tool_calls and is_question:
        clarification_count += 1

    return {
        "messages": [response],
        "clarification_count": clarification_count,
        "loop_count": state.get("loop_count", 0),
    }

def should_continue(state: AgentState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "end"
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        loop_count = state.get("loop_count", 0) + 1
        state["loop_count"] = loop_count
        if loop_count > 5:
            messages.append(
                SystemMessage(
                    content="Execution stopped: Maximum tool execution limit (5 loops) reached to prevent quota exhaustion."
                )
            )
            logger.warning("Maximum tool execution limit (5 loops) reached.")
            return "end"
        return "tools"
    return "end"

async def execute_tools(state: AgentState) -> dict[str, Any]:
    messages = state.get("messages", [])
    if not messages:
        return {"messages": []}

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    tool_messages = []

    for call in tool_calls:
        tool_name = call.get("name")
        tool_args = call.get("args", {})
        call_id = call.get("id", "")
        target_tool = tool_map.get(tool_name)

        if target_tool is not None:
            try:
                args_str = json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)
                logger.info(f"\n{'='*50}\nTOOL EXECUTION: {tool_name}\nArguments: {args_str}\n{'='*50}\n")
                result = await target_tool.ainvoke(tool_args)
                res_str = str(result)
                res_preview = res_str[:300] + "..." if len(res_str) > 300 else res_str
                logger.info(f"\n{'='*50}\nTOOL COMPLETED: {tool_name}\nOutput: {res_preview}\n{'='*50}\n")
            except Exception as exc:
                result = {"error": str(exc)}
                logger.error(f"\n{'!'*50}\nTOOL FAILED: {tool_name}\nError: {exc}\n{'!'*50}\n")
        else:
            result = {"error": f"Tool '{tool_name}' not recognized"}
            logger.error(f"\n{'!'*50}\nTOOL NOT RECOGNIZED: {tool_name}\n{'!'*50}\n")

        tool_messages.append(
            ToolMessage(
                content=str(result),
                name=tool_name,
                tool_call_id=call_id,
            )
        )

    return {
        "messages": tool_messages,
    }
