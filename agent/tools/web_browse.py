"""
Web browsing via Firecrawl API.
Returns clean markdown of a page.
Falls back to requests+BeautifulSoup if FIRECRAWL_API_KEY is not set or Firecrawl errors.
"""
import re


def web_browse(url: str) -> str:
    """
    Fetch a URL via Firecrawl and return clean markdown content.
    Falls back to requests+BeautifulSoup if Firecrawl is unavailable.
    """
    try:
        text = _browse_firecrawl(url)
    except Exception:
        text = _browse_requests(url)

    if len(text) > 8000:
        text = text[:8000] + "\n\n[... page truncated ...]"
    return text


def _browse_firecrawl(url: str) -> str:
    import os
    from firecrawl import FirecrawlApp

    api_key = os.environ.get("FIRECRAWL_API_KEY", "")
    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY not set")
    app = FirecrawlApp(api_key=api_key)
    result = app.scrape_url(url, formats=["markdown"])
    return result.markdown or ""


def _browse_requests(url: str) -> str:
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script/style tags
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    return _clean_text(text)


def _clean_text(text: str) -> str:
    # Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


from agent.tools.registry import tool  # noqa: E402


@tool({
    "name": "web_browse",
    "description": "Fetch and read the text content of a web page. Returns cleaned plain text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to browse"},
        },
        "required": ["url"],
    },
})
def _handle(inputs: dict, **_) -> tuple[str, bool]:
    text = web_browse(inputs["url"])
    return text, False
