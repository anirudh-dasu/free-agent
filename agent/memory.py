import sqlite3
import json
import os
from datetime import datetime, timezone

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

DB_PATH = os.environ.get("DB_PATH", "/app/data/agent.db")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "/app/data/chroma")

_chroma_client = None
_chroma_col = None


def _get_chroma_col():
    global _chroma_client, _chroma_col
    if _chroma_col is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        _chroma_col = _chroma_client.get_or_create_collection(
            name="memories", embedding_function=ef
        )
    return _chroma_col


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                content TEXT,
                importance INTEGER,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                slug TEXT UNIQUE,
                content_md TEXT,
                session_id INTEGER,
                published_at TEXT,
                twitter_url TEXT,
                bluesky_url TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT,
                ended_at TEXT,
                summary TEXT,
                actions_json TEXT
            );

            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                from_addr TEXT,
                subject TEXT,
                body TEXT,
                received_at TEXT,
                replied_at TEXT,
                reply_body TEXT
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                due_date TEXT,
                note TEXT,
                created_at TEXT,
                triggered_at TEXT
            );
        """)

    # Initialize ChromaDB and sync any existing SQLite memories not yet indexed
    col = _get_chroma_col()
    existing_ids = set(col.get()["ids"])
    rows = get_all_memories(limit=1000)
    to_add = [r for r in rows if str(r["id"]) not in existing_ids]
    if to_add:
        col.add(
            ids=[str(r["id"]) for r in to_add],
            documents=[r["content"] for r in to_add],
            metadatas=[{"category": r["category"], "importance": r["importance"]} for r in to_add],
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Session CRUD ──────────────────────────────────────────────────────────────

def start_session() -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (started_at, actions_json) VALUES (?, ?)",
            (now_iso(), "[]"),
        )
        return cur.lastrowid


def end_session(session_id: int, summary: str, actions: list) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET ended_at=?, summary=?, actions_json=? WHERE id=?",
            (now_iso(), summary, json.dumps(actions), session_id),
        )


def get_recent_sessions(n: int = 5) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE summary IS NOT NULL ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def is_first_session() -> bool:
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    return count == 0


# ── Memory CRUD ───────────────────────────────────────────────────────────────

def remember(category: str, content: str, importance: int) -> int:
    importance = max(1, min(5, importance))
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO memories (category, content, importance, created_at) VALUES (?, ?, ?, ?)",
            (category, content, importance, now_iso()),
        )
        mid = cur.lastrowid
    _get_chroma_col().add(
        ids=[str(mid)],
        documents=[content],
        metadatas=[{"category": category, "importance": importance}],
    )
    return mid


def recall(query: str, limit: int = 20) -> list[dict]:
    """Semantic search over memories using ChromaDB embeddings."""
    col = _get_chroma_col()
    if col.count() == 0:
        return []
    results = col.query(query_texts=[query], n_results=min(limit, col.count()))
    ids   = results["ids"][0]
    metas = results["metadatas"][0]
    docs  = results["documents"][0]
    return [
        {
            "id":         int(ids[i]),
            "category":   metas[i]["category"],
            "content":    docs[i],
            "importance": metas[i]["importance"],
        }
        for i in range(len(ids))
    ]


def get_all_memories(limit: int = 50) -> list[dict]:
    """Return top memories sorted by importance for system prompt injection."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY importance DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Memory management ────────────────────────────────────────────────────────

def delete_memory(memory_id: int) -> bool:
    """Delete a memory by ID. Returns True if a row was deleted."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        deleted = cur.rowcount > 0
    if deleted:
        try:
            _get_chroma_col().delete(ids=[str(memory_id)])
        except Exception:
            pass  # ChromaDB delete is best-effort; SQLite is source of truth
    return deleted


# ── Post CRUD ─────────────────────────────────────────────────────────────────

def list_posts(limit: int = 50) -> list[dict]:
    """Return all published posts, newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, slug, published_at FROM posts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def read_post(slug: str) -> dict | None:
    """Return a single post's full content by slug."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM posts WHERE slug=?", (slug,)
        ).fetchone()
    return dict(row) if row else None


def save_post(title: str, slug: str, content_md: str, session_id: int,
              twitter_url: str = None, bluesky_url: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO posts (title, slug, content_md, session_id, published_at, twitter_url, bluesky_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                content_md=excluded.content_md,
                published_at=excluded.published_at,
                twitter_url=excluded.twitter_url,
                bluesky_url=excluded.bluesky_url
            """,
            (title, slug, content_md, session_id, now_iso(), twitter_url, bluesky_url),
        )
        return cur.lastrowid


# ── Email CRUD ────────────────────────────────────────────────────────────────

def upsert_email(message_id: str, from_addr: str, subject: str,
                 body: str, received_at: str) -> None:
    """Insert a new email record; silently ignore if message_id already exists."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO emails (message_id, from_addr, subject, body, received_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, from_addr, subject, body, received_at),
        )


def mark_email_replied(message_id: str, reply_body: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE emails SET replied_at=?, reply_body=? WHERE message_id=?",
            (now_iso(), reply_body, message_id),
        )


def get_seen_message_ids() -> set:
    """Return all message_ids already stored in the emails table."""
    with get_conn() as conn:
        rows = conn.execute("SELECT message_id FROM emails").fetchall()
    return {r[0] for r in rows}


# ── Reminder CRUD ─────────────────────────────────────────────────────────────

def set_reminder(due_date: str, note: str) -> int:
    """Create a reminder. due_date should be YYYY-MM-DD. Returns the new id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (due_date, note, created_at) VALUES (?, ?, ?)",
            (due_date, note, now_iso()),
        )
        return cur.lastrowid


def get_due_reminders(today: str) -> list[dict]:
    """Return reminders whose due_date <= today that haven't been triggered yet."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM reminders
            WHERE due_date <= ? AND triggered_at IS NULL
            ORDER BY due_date
            """,
            (today,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_reminders_triggered(ids: list) -> None:
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    with get_conn() as conn:
        conn.execute(
            f"UPDATE reminders SET triggered_at=? WHERE id IN ({placeholders})",
            [now_iso()] + list(ids),
        )
