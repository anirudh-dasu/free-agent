"""
One-time setup: create an AgentMail inbox for the agent.

Run once:
    python setup_email.py

Then add the printed AGENTMAIL_INBOX_ID to your .env file.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("AGENTMAIL_API_KEY", "")
if not api_key:
    print("ERROR: AGENTMAIL_API_KEY is not set in your environment or .env file.")
    print("Get a free API key at https://agentmail.to")
    sys.exit(1)

try:
    from agentmail import AgentMail
except ImportError:
    print("ERROR: agentmail package not installed. Run: pip install agentmail")
    sys.exit(1)

client = AgentMail(api_key=api_key)

# Use a deterministic username so re-running is idempotent
username = os.environ.get("AGENTMAIL_USERNAME", "free-agent")

print(f"Creating inbox with username '{username}' on agentmail.to ...")

try:
    inbox = client.inboxes.create(username=username, domain="agentmail.to")
except Exception as e:
    # If inbox already exists the SDK may raise — just list and find it
    print(f"Create call returned: {e}")
    print("Attempting to list existing inboxes ...")
    inboxes = client.inboxes.list()
    inbox = next((i for i in inboxes if getattr(i, "username", "") == username), None)
    if inbox is None:
        print("Could not create or find inbox. Check your API key and try again.")
        sys.exit(1)

inbox_id = inbox.inbox_id
address = getattr(inbox, "address", f"{username}@agentmail.to")

print()
print("=" * 60)
print(f"  Inbox created!")
print(f"  Address : {address}")
print(f"  Inbox ID: {inbox_id}")
print()
print("  Add to your .env:")
print(f"  AGENTMAIL_INBOX_ID={inbox_id}")
print("=" * 60)
