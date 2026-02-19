"""
Entry point — daily session orchestrator.

Reads environment, initialises DB, builds context from memory/sessions,
then hands off to the agentic brain.
"""
import os
import sys
from dotenv import load_dotenv

# Load .env before any other imports that might read env vars
load_dotenv()

from agent import memory as mem
from agent.persona import build_system_prompt
from agent.brain import run_session


def main() -> None:
    # ── Validate required environment variables ──────────────────────────────
    required = [
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
        "GITHUB_BLOG_REPO",
        "GITHUB_PAGES_URL",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[main] ERROR: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # ── Initialise database ──────────────────────────────────────────────────
    mem.init_db()

    # ── Determine session context ────────────────────────────────────────────
    first_session = mem.is_first_session()
    memories = [] if first_session else mem.get_all_memories(limit=50)
    recent_sessions = [] if first_session else mem.get_recent_sessions(n=5)

    if first_session:
        print("[main] First session detected — agent starts as blank slate.")
    else:
        print(f"[main] Loaded {len(memories)} memories, {len(recent_sessions)} recent sessions.")

    # ── Build system prompt ──────────────────────────────────────────────────
    system_prompt = build_system_prompt(
        is_first_session=first_session,
        memories=memories,
        recent_sessions=recent_sessions,
    )

    # ── Start session record ─────────────────────────────────────────────────
    session_id = mem.start_session()
    print(f"[main] Session {session_id} started.")

    # ── Run agentic loop ─────────────────────────────────────────────────────
    summary = run_session(system_prompt=system_prompt, session_id=session_id)

    print(f"\n[main] Session {session_id} complete.")
    print(f"[main] Summary: {summary}")


if __name__ == "__main__":
    main()
