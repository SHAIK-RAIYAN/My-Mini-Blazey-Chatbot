from typing import Any
import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field
from app.config import settings

class TavilySearchArgs(BaseModel):
    query: str = Field(..., description="Search query string to find information on the web")

@tool(description="Execute web search using Tavily API and return synthesized answer snippets", args_schema=TavilySearchArgs)
async def tavily_search(query: str) -> str:
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        return "Error: TAVILY_API_KEY is not configured in settings."

    endpoint = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "include_answer": True,
        "search_depth": "basic",
        "max_results": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return f"Web search request failed: {str(exc)}"

    answer = data.get("answer")
    if answer:
        return str(answer)

    results = data.get("results", [])
    snippets = [
        f"{r.get('title', 'Result')}: {r.get('content', '')}"
        for r in results
        if r.get("content")
    ]
    if snippets:
        return "\n\n".join(snippets)

    return "No search results found for the query."
