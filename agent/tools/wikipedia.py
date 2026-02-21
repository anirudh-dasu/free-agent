"""
Wikipedia summary lookup via the REST v1 API.
No API key required.
"""
import urllib.parse
import requests


def get_wikipedia(topic: str) -> dict:
    """
    Return a summary for a Wikipedia topic.
    Falls back to search if the direct page lookup returns 404.
    Returns: {title, extract, url}
    """
    encoded = urllib.parse.quote(topic.replace(" ", "_"))
    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"

    resp = requests.get(summary_url, timeout=10, headers={"User-Agent": "free-agent/1.0"})

    if resp.status_code == 200:
        data = resp.json()
        return {
            "title": data.get("title", topic),
            "extract": data.get("extract", ""),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }

    # 404 or redirect — try opensearch
    if resp.status_code in (404, 301, 302):
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "opensearch",
            "search": topic,
            "limit": 1,
            "format": "json",
        }
        search_resp = requests.get(search_url, params=params, timeout=10,
                                   headers={"User-Agent": "free-agent/1.0"})
        search_resp.raise_for_status()
        results = search_resp.json()
        # results = [query, [titles], [descriptions], [urls]]
        if results[1]:
            first_title = results[1][0]
            return get_wikipedia(first_title)
        return {"error": f"No Wikipedia page found for '{topic}'"}

    resp.raise_for_status()
    return {"error": f"Unexpected status {resp.status_code}"}


import json  # noqa: E402
from agent.tools.registry import tool  # noqa: E402


@tool({
    "name": "get_wikipedia",
    "description": "Look up a Wikipedia article summary for a topic. Returns the title, extract, and URL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "The topic or article title to look up"},
        },
        "required": ["topic"],
    },
})
def _handle(inputs: dict, **_) -> tuple[str, bool]:
    return json.dumps(get_wikipedia(inputs["topic"]), indent=2), False
