"""
Tool handler for end_session.
Needs both session_id and actions from the dispatch context.
"""
from agent import memory as mem
from agent.tools.registry import tool


@tool({
    "name": "end_session",
    "description": "End today's session. Write a summary of what you did and learned. This exits the loop.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "A concise summary of today's session (2-5 sentences)",
            },
        },
        "required": ["summary"],
    },
})
def _handle(inputs: dict, *, session_id: int = 0, actions: list = None, **_) -> tuple[str, bool]:
    mem.end_session(session_id, inputs["summary"], actions or [])
    try:
        from agent.tools.blog import push_session_summary
        push_session_summary(session_id, inputs["summary"])
    except Exception as e:
        print(f"[brain] Could not push session summary to blog: {e}")
    return inputs["summary"], True
