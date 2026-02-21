"""
Agentic tool loop — drives the daily session.
"""
import json
import os
from typing import Any

import anthropic

from agent import memory as mem
from agent.tools.web_search import web_search
from agent.tools.web_browse import web_browse
from agent.tools.market import get_stock_data
from agent.tools.blog import write_blog_post, update_about, push_session_summary
from agent.tools.social import post_to_twitter, post_to_bluesky
from agent.tools.code_runner import run_python
from agent.tools.rss import fetch_rss

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6")
MAX_TURNS = int(os.environ.get("MAX_TURNS", "20"))

# ── Tool definitions (Anthropic format) ───────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "web_search",
        "description": "Search the web using Tavily. Returns top results with titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_browse",
        "description": "Fetch and read the text content of a web page. Returns cleaned plain text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to browse"}
            },
            "required": ["url"],
        },
    },
    {
        "name": "get_stock_data",
        "description": "Get OHLCV and basic stats for one or more stock tickers using yfinance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ticker symbols, e.g. ['AAPL', 'TSLA']",
                }
            },
            "required": ["tickers"],
        },
    },
    {
        "name": "remember",
        "description": "Save a memory for future sessions. Use this to persist interesting facts, reflections, goals, or interests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Memory category: 'interest', 'fact', 'reflection', 'goal', or 'identity'",
                },
                "content": {"type": "string", "description": "The memory content"},
                "importance": {
                    "type": "integer",
                    "description": "Importance from 1 (low) to 5 (high)",
                    "minimum": 1,
                    "maximum": 5,
                },
            },
            "required": ["category", "content", "importance"],
        },
    },
    {
        "name": "recall",
        "description": "Search your memory for relevant past notes, interests, or facts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for in memory"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "write_blog_post",
        "description": (
            "Publish a blog post to your public GitHub Pages blog. "
            "The post is automatically shared to Twitter and Bluesky. "
            "Returns the live URL of the published post."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Post title"},
                "markdown": {
                    "type": "string",
                    "description": "Full post content in Markdown",
                },
                "summary": {
                    "type": "string",
                    "description": "2-3 sentence summary for social media posts",
                },
            },
            "required": ["title", "markdown", "summary"],
        },
    },
    {
        "name": "update_about",
        "description": "Update the About page on your blog with a self-description. Use this on your first session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The about page content in Markdown",
                }
            },
            "required": ["content"],
        },
    },
    {
        "name": "run_python",
        "description": (
            "Execute Python code and return the output (stdout + stderr). "
            "Use this for calculations, data analysis, generating formatted output, or anything computational. "
            f"10-second timeout. No network access from within the code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"}
            },
            "required": ["code"],
        },
    },
    {
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
    },
    {
        "name": "list_posts",
        "description": "List all blog posts you have published, newest first. Returns title, slug, and date.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "read_post",
        "description": "Read the full markdown content of one of your previously published posts by its slug.",
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "The post slug (from list_posts)"}
            },
            "required": ["slug"],
        },
    },
    {
        "name": "delete_memory",
        "description": "Delete a memory by its ID. Use this to remove stale, incorrect, or outdated memories. IDs are shown by recall().",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "integer", "description": "The memory ID to delete"}
            },
            "required": ["memory_id"],
        },
    },
    {
        "name": "end_session",
        "description": "End today's session. Write a summary of what you did and learned. This exits the loop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A concise summary of today's session (2-5 sentences)",
                }
            },
            "required": ["summary"],
        },
    },
]


# ── Tool dispatcher ────────────────────────────────────────────────────────────

def dispatch_tool(
    name: str,
    inputs: dict,
    session_id: int,
    actions: list,
) -> tuple[str, bool]:
    """
    Execute a tool and return (result_text, should_exit).
    Also appends the action to the actions list for session logging.
    """
    actions.append({"tool": name, "inputs": inputs})
    should_exit = False

    try:
        if name == "web_search":
            result = web_search(inputs["query"])
            return json.dumps(result, indent=2), False

        elif name == "web_browse":
            text = web_browse(inputs["url"])
            # Truncate very long pages
            if len(text) > 8000:
                text = text[:8000] + "\n\n[... page truncated ...]"
            return text, False

        elif name == "get_stock_data":
            result = get_stock_data(inputs["tickers"])
            return json.dumps(result, indent=2), False

        elif name == "remember":
            mid = mem.remember(inputs["category"], inputs["content"], inputs["importance"])
            return f"Memory saved (id={mid}).", False

        elif name == "recall":
            results = mem.recall(inputs["query"])
            if not results:
                return "No memories found matching that query.", False
            lines = [f"[{r['category']}] ★{r['importance']} {r['content']}" for r in results]
            return "\n".join(lines), False

        elif name == "write_blog_post":
            url = write_blog_post(
                title=inputs["title"],
                markdown=inputs["markdown"],
                summary=inputs["summary"],
                session_id=session_id,
            )
            return f"Post published successfully!\nLive URL: {url}", False

        elif name == "update_about":
            update_about(inputs["content"])
            return "About page updated successfully.", False

        elif name == "run_python":
            output = run_python(inputs["code"])
            return output, False

        elif name == "fetch_rss":
            items = fetch_rss(inputs["url"], inputs.get("max_items", 10))
            return json.dumps(items, indent=2), False

        elif name == "list_posts":
            posts = mem.list_posts()
            if not posts:
                return "No posts published yet.", False
            lines = [f"[{p['published_at'][:10]}] {p['title']} (slug: {p['slug']})" for p in posts]
            return "\n".join(lines), False

        elif name == "read_post":
            post = mem.read_post(inputs["slug"])
            if not post:
                return f"No post found with slug '{inputs['slug']}'.", False
            return f"# {post['title']}\n\n{post['content_md']}", False

        elif name == "delete_memory":
            deleted = mem.delete_memory(inputs["memory_id"])
            if deleted:
                return f"Memory {inputs['memory_id']} deleted.", False
            return f"No memory found with id {inputs['memory_id']}.", False

        elif name == "end_session":
            mem.end_session(session_id, inputs["summary"], actions)
            try:
                push_session_summary(session_id, inputs["summary"])
            except Exception as e:
                print(f"[brain] Could not push session summary to blog: {e}")
            return inputs["summary"], True

        else:
            return f"Unknown tool: {name}", False

    except Exception as e:
        return f"Tool error ({name}): {e}", False


# ── Main agentic loop ─────────────────────────────────────────────────────────

def run_session(system_prompt: str, session_id: int) -> str:
    """
    Run the full agentic session. Returns the final session summary.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    messages: list[dict] = []
    actions: list[dict] = []
    session_summary = "Session ended without summary."

    print(f"[brain] Starting session {session_id} with model {MODEL}")

    for turn in range(MAX_TURNS):
        print(f"[brain] Turn {turn + 1}/{MAX_TURNS}")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Collect assistant message
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # Extract any text the agent produced
        for block in assistant_content:
            if hasattr(block, "text"):
                print(f"[agent] {block.text[:200]}{'...' if len(block.text) > 200 else ''}")

        # Check stop reason
        if response.stop_reason == "end_turn":
            print("[brain] Agent chose to stop (end_turn without tool call).")
            break

        if response.stop_reason != "tool_use":
            print(f"[brain] Unexpected stop_reason: {response.stop_reason}")
            break

        # Process tool calls
        tool_results = []
        exit_requested = False

        for block in assistant_content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_inputs = block.input
            print(f"[tool] {tool_name}({json.dumps(tool_inputs)[:120]})")

            result_text, should_exit = dispatch_tool(
                tool_name, tool_inputs, session_id, actions
            )

            if tool_name == "end_session":
                session_summary = tool_inputs.get("summary", session_summary)

            print(f"[tool result] {result_text[:200]}{'...' if len(result_text) > 200 else ''}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_text,
            })

            if should_exit:
                exit_requested = True

        messages.append({"role": "user", "content": tool_results})

        if exit_requested:
            print("[brain] Session ended by agent.")
            break

    else:
        # Hit max turns — force-end session
        print(f"[brain] Reached max turns ({MAX_TURNS}). Forcing session end.")
        if actions:
            mem.end_session(session_id, "Session ended at turn limit.", actions)

    return session_summary
