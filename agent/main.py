"""
Entry point — daily session orchestrator.

Reads environment, initialises DB, builds context from memory/sessions,
then hands off to the agentic brain.
"""
import os
import sys
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load .env before any other imports that might read env vars
load_dotenv()

from agent import memory as mem
from agent.persona import build_system_prompt
from agent.brain import run_session


def main() -> None:
    # ── Validate required environment variables ──────────────────────────────
    required = ["ANTHROPIC_API_KEY"]
    if not os.environ.get("LOCAL_MODE", "").lower() == "true":
        required += ["GITHUB_TOKEN", "GITHUB_BLOG_REPO", "GITHUB_PAGES_URL"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[main] ERROR: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    local_mode = os.environ.get("LOCAL_MODE", "").lower() == "true"
    if local_mode:
        print("[main] LOCAL MODE — posts go to ./output/, social posts are logged only.")

    loop_interval: int | None = None
    if local_mode:
        raw = os.environ.get("LOCAL_LOOP_INTERVAL", "").strip()
        if raw:
            try:
                loop_interval = int(raw)
                print(f"[main] Loop interval: {loop_interval} minute(s). Press Ctrl-C to stop.")
            except ValueError:
                print(f"[main] WARNING: LOCAL_LOOP_INTERVAL={raw!r} is not an integer — running once.")

    # ── Initialise database ──────────────────────────────────────────────────
    mem.init_db()

    while True:
        _run_one_session()
        if loop_interval is None:
            break
        print(f"\n[main] Sleeping {loop_interval} minute(s) until next session… (Ctrl-C to stop)")
        time.sleep(loop_interval * 60)


def _run_one_session() -> None:
    # ── Determine session context ────────────────────────────────────────────
    first_session = mem.is_first_session()
    memories = [] if first_session else mem.get_all_memories(limit=50)
    recent_sessions = [] if first_session else mem.get_recent_sessions(n=5)

    if first_session:
        print("[main] First session detected — agent starts as blank slate.")
    else:
        print(f"[main] Loaded {len(memories)} memories, {len(recent_sessions)} recent sessions.")

    # ── Email unread count ───────────────────────────────────────────────────
    unread_count = 0
    try:
        from agent.tools.email_reader import get_unread_count
        unread_count = get_unread_count()
        if unread_count:
            print(f"[main] {unread_count} unread email(s).")
    except Exception as e:
        print(f"[main] Could not check email: {e}")

    # ── Due reminders ────────────────────────────────────────────────────────
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    due_reminders = mem.get_due_reminders(today)
    if due_reminders:
        mem.mark_reminders_triggered([r["id"] for r in due_reminders])
        print(f"[main] {len(due_reminders)} reminder(s) due today.")

    # ── Build system prompt ──────────────────────────────────────────────────
    system_prompt = build_system_prompt(
        is_first_session=first_session,
        memories=memories,
        recent_sessions=recent_sessions,
        unread_count=unread_count,
        due_reminders=due_reminders,
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
