"""
Web search via Tavily API.
Free tier: 1000 searches/month.
"""
import os
import requests


TAVILY_API_URL = "https://api.tavily.com/search"


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using Tavily.
    Returns a list of {title, url, snippet} dicts.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set")

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
    }

    response = requests.post(TAVILY_API_URL, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    results = []

    # Include Tavily's synthesized answer if present
    if data.get("answer"):
        results.append({
            "type": "answer",
            "content": data["answer"],
        })

    for r in data.get("results", []):
        results.append({
            "type": "result",
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", "")[:500],
        })

    return results


import json  # noqa: E402
from agent.tools.registry import tool  # noqa: E402


@tool({
    "name": "web_search",
    "description": "Search the web using Tavily. Returns top results with titles, URLs, and snippets.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
        },
        "required": ["query"],
    },
})
def _handle(inputs: dict, **_) -> tuple[str, bool]:
    return json.dumps(web_search(inputs["query"]), indent=2), False
