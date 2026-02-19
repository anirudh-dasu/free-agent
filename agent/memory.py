import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH", "/app/data/agent.db")


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
        """)


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
        return cur.lastrowid


def recall(query: str, limit: int = 20) -> list[dict]:
    """Simple full-text search over memory content."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM memories
            WHERE content LIKE ? OR category LIKE ?
            ORDER BY importance DESC, id DESC
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_memories(limit: int = 50) -> list[dict]:
    """Return top memories sorted by importance for system prompt injection."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY importance DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Post CRUD ─────────────────────────────────────────────────────────────────

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
