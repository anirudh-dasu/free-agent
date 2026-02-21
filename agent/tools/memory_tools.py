"""
Tool handlers for memory-related operations.
Wraps functions from agent.memory (remember, recall, delete_memory,
list_posts, read_post, set_reminder) — none of these had a dedicated
tool module before this refactor.
"""
from agent import memory as mem
from agent.tools.registry import tool


@tool({
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
})
def _handle_remember(inputs: dict, **_) -> tuple[str, bool]:
    mid = mem.remember(inputs["category"], inputs["content"], inputs["importance"])
    return f"Memory saved (id={mid}).", False


@tool({
    "name": "recall",
    "description": "Search your memory for relevant past notes, interests, or facts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for in memory"},
        },
        "required": ["query"],
    },
})
def _handle_recall(inputs: dict, **_) -> tuple[str, bool]:
    results = mem.recall(inputs["query"])
    if not results:
        return "No memories found matching that query.", False
    lines = [f"[{r['category']}] ★{r['importance']} {r['content']}" for r in results]
    return "\n".join(lines), False


@tool({
    "name": "delete_memory",
    "description": "Delete a memory by its ID. Use this to remove stale, incorrect, or outdated memories. IDs are shown by recall().",
    "input_schema": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "integer", "description": "The memory ID to delete"},
        },
        "required": ["memory_id"],
    },
})
def _handle_delete(inputs: dict, **_) -> tuple[str, bool]:
    deleted = mem.delete_memory(inputs["memory_id"])
    if deleted:
        return f"Memory {inputs['memory_id']} deleted.", False
    return f"No memory found with id {inputs['memory_id']}.", False


@tool({
    "name": "list_posts",
    "description": "List all blog posts you have published, newest first. Returns title, slug, and date.",
    "input_schema": {
        "type": "object",
        "properties": {},
    },
})
def _handle_list_posts(inputs: dict, **_) -> tuple[str, bool]:
    posts = mem.list_posts()
    if not posts:
        return "No posts published yet.", False
    lines = [f"[{p['published_at'][:10]}] {p['title']} (slug: {p['slug']})" for p in posts]
    return "\n".join(lines), False


@tool({
    "name": "read_post",
    "description": "Read the full markdown content of one of your previously published posts by its slug.",
    "input_schema": {
        "type": "object",
        "properties": {
            "slug": {"type": "string", "description": "The post slug (from list_posts)"},
        },
        "required": ["slug"],
    },
})
def _handle_read_post(inputs: dict, **_) -> tuple[str, bool]:
    post = mem.read_post(inputs["slug"])
    if not post:
        return f"No post found with slug '{inputs['slug']}'.", False
    return f"# {post['title']}\n\n{post['content_md']}", False


@tool({
    "name": "set_reminder",
    "description": "Set a reminder note for a future date. The reminder will be injected into your system prompt on or after the due date.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
            "note": {"type": "string", "description": "What to remind yourself about"},
        },
        "required": ["date", "note"],
    },
})
def _handle_set_reminder(inputs: dict, **_) -> tuple[str, bool]:
    rid = mem.set_reminder(inputs["date"], inputs["note"])
    return f"Reminder set (id={rid}) for {inputs['date']}: {inputs['note']}", False
