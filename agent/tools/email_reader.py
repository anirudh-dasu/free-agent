"""
Email reader via AgentMail.to REST SDK.

The agent can read its inbox and reply to messages.
Sending to arbitrary addresses is intentionally not supported.
"""
import os
from datetime import datetime, timezone

from agent import memory as mem

AGENTMAIL_API_KEY = os.environ.get("AGENTMAIL_API_KEY", "")
AGENTMAIL_INBOX_ID = os.environ.get("AGENTMAIL_INBOX_ID", "")


def _client():
    from agentmail import AgentMail
    return AgentMail(api_key=AGENTMAIL_API_KEY)


def get_unread_count() -> int:
    """Return how many emails in the inbox have not yet been seen by the agent."""
    if not AGENTMAIL_API_KEY or not AGENTMAIL_INBOX_ID:
        return 0
    try:
        client = _client()
        msgs = client.inboxes.messages.list(AGENTMAIL_INBOX_ID, limit=50)
        seen = mem.get_seen_message_ids()
        return sum(1 for m in msgs if m.message_id not in seen)
    except Exception as e:
        print(f"[email] get_unread_count error: {e}")
        return 0


def read_inbox(max_emails: int = 10) -> list[dict]:
    """
    Fetch recent messages, upsert into the emails table, and return them.
    Returns a list of dicts: {message_id, from_addr, subject, body, received_at}.
    """
    if not AGENTMAIL_API_KEY or not AGENTMAIL_INBOX_ID:
        return [{"error": "AgentMail not configured (AGENTMAIL_API_KEY / AGENTMAIL_INBOX_ID missing)."}]

    client = _client()
    msgs = client.inboxes.messages.list(AGENTMAIL_INBOX_ID, limit=max_emails)

    results = []
    for m in msgs:
        message_id = m.message_id
        from_addr = getattr(m, "from_address", "") or ""
        subject = getattr(m, "subject", "") or ""
        body = getattr(m, "text", "") or getattr(m, "body", "") or ""
        received_at = getattr(m, "received_at", "") or datetime.now(timezone.utc).isoformat()

        mem.upsert_email(message_id, from_addr, subject, body, received_at)
        results.append({
            "message_id": message_id,
            "from": from_addr,
            "subject": subject,
            "body": body[:2000],  # cap per message
            "received_at": received_at,
        })

    return results


def reply_email(message_id: str, body: str) -> str:
    """Reply to an email by message_id. Updates the DB with reply timestamp."""
    if not AGENTMAIL_API_KEY or not AGENTMAIL_INBOX_ID:
        return "AgentMail not configured."

    client = _client()
    client.inboxes.messages.reply(AGENTMAIL_INBOX_ID, message_id, text=body)
    mem.mark_email_replied(message_id, body)
    return f"Reply sent to message {message_id}."
