# Import all tool modules (side-effect: triggers @tool registrations).
# Order here determines the TOOLS list order visible to the agent.
from agent.tools import (  # noqa: F401
    web_search,
    web_browse,
    market,
    rss,
    code_runner,
    wikipedia,
    weather,
    downloader,
    blog,
    email_reader,
    memory_tools,
    session_tools,
)
from agent.tools.registry import get_tools, get_dispatch

TOOLS = get_tools()
DISPATCH = get_dispatch()
