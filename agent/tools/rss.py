"""
RSS / Atom feed fetcher via feedparser.
Lets the agent read news, blogs, arXiv, HN etc. without burning search credits.
"""
from __future__ import annotations

import feedparser


def fetch_rss(url: str, max_items: int = 10) -> list[dict]:
    """
    Fetch and parse an RSS or Atom feed.
    Returns up to max_items entries as [{title, link, summary, published}].
    """
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        raise RuntimeError(f"Failed to parse feed at {url}: {feed.bozo_exception}")

    items = []
    for entry in feed.entries[:max_items]:
        items.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "summary": _truncate(entry.get("summary", ""), 300),
            "published": entry.get("published", ""),
        })

    return items


def _truncate(text: str, limit: int) -> str:
    # Strip basic HTML tags from summary
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()
    return text[:limit] + ("..." if len(text) > limit else "")


import json  # noqa: E402
from agent.tools.registry import tool  # noqa: E402


@tool({
    "name": "fetch_rss",
    "description": (
        "Fetch and parse an RSS or Atom feed. "
        "Use this to read news sites, HN, arXiv, blogs, or any feed URL. "
        "Returns titles, links, summaries, and publish dates."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The RSS/Atom feed URL"},
            "max_items": {
                "type": "integer",
                "description": "Max number of items to return (default 10)",
                "default": 10,
            },
        },
        "required": ["url"],
    },
})
def _handle(inputs: dict, **_) -> tuple[str, bool]:
    return json.dumps(fetch_rss(inputs["url"], inputs.get("max_items", 10)), indent=2), False
