"""
Agentic tool loop — drives the daily session.
"""
import json
import os

import anthropic

from agent import memory as mem
from agent.tools import TOOLS, DISPATCH

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6")
MAX_TURNS = int(os.environ.get("MAX_TURNS", "20"))


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
    handler = DISPATCH.get(name)
    if not handler:
        return f"Unknown tool: {name}", False
    try:
        return handler(inputs, session_id=session_id, actions=actions)
    except Exception as e:
        return f"Tool error ({name}): {e}", False


# ── Main agentic loop ─────────────────────────────────────────────────────────

def run_session(system_prompt: str, session_id: int) -> str:
    """
    Run the full agentic session. Returns the final session summary.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages: list[dict] = [
        {"role": "user", "content": f"Today is {today}. Begin your session."},
    ]
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
