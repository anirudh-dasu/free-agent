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
