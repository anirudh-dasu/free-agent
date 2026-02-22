"""
Blog publishing via GitHub REST API → GitHub Pages (Jekyll).
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
from datetime import datetime, timezone

import requests

from agent.tools.social import share_post
from agent import memory as mem


def _is_local() -> bool:
    return os.environ.get("LOCAL_MODE", "").lower() == "true"


def _github_headers() -> dict:
    token = os.environ["GITHUB_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo() -> str:
    return os.environ["GITHUB_BLOG_REPO"]


def _pages_url() -> str:
    return os.environ["GITHUB_PAGES_URL"].rstrip("/")


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:60]


def _get_file_sha(path: str) -> str | None:
    """Return the blob SHA of an existing file, or None if it doesn't exist."""
    url = f"https://api.github.com/repos/{_repo()}/contents/{path}"
    response = requests.get(url, headers=_github_headers(), timeout=15)
    if response.status_code == 200:
        return response.json().get("sha")
    return None


def _put_file(path: str, content: str, commit_message: str) -> None:
    """Create or update a file in the GitHub repo."""
    url = f"https://api.github.com/repos/{_repo()}/contents/{path}"

    sha = _get_file_sha(path)
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    payload: dict = {
        "message": commit_message,
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(url, headers=_github_headers(), json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(
            f"GitHub API error {response.status_code}: {response.text[:300]}"
        )


def _build_jekyll_front_matter(title: str, date: str, slug: str) -> str:
    return f"""---
layout: post
title: "{title.replace('"', '\\"')}"
date: {date}
slug: {slug}
---
"""


def write_blog_post(
    title: str,
    markdown: str,
    summary: str,
    session_id: int,
) -> str:
    """
    Publish a blog post to GitHub Pages and share to social media.
    Returns the live post URL.
    """
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%Y-%m-%d")
    datetime_str = today.strftime("%Y-%m-%d %H:%M:%S +0000")
    slug = _slugify(title)

    filename = f"_posts/{date_str}-{slug}.md"
    front_matter = _build_jekyll_front_matter(title, datetime_str, slug)
    jekyll_content = front_matter + "\n" + markdown

    if _is_local():
        out_dir = pathlib.Path("output/posts")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{date_str}-{slug}.md").write_text(jekyll_content)
        mem.save_post(title, slug, markdown, session_id, twitter_url=None, bluesky_url=None)
        _append_session_log(session_id, title, f"[local] output/posts/{date_str}-{slug}.md")
        return f"[LOCAL] Post written to output/posts/{date_str}-{slug}.md"

    _put_file(
        path=filename,
        content=jekyll_content,
        commit_message=f"Post: {title}",
    )

    post_url = f"{_pages_url()}/{date_str.replace('-', '/')}/{slug}/"

    # Share to social
    social_results = share_post(title=title, summary=summary, url=post_url)

    # Persist to local DB
    mem.save_post(
        title=title,
        slug=slug,
        content_md=markdown,
        session_id=session_id,
        twitter_url=social_results.get("twitter"),
        bluesky_url=social_results.get("bluesky"),
    )

    # Update sessions.json on the blog
    _append_session_log(session_id=session_id, post_title=title, post_url=post_url)

    return post_url


def update_about(content: str) -> str:
    """Update the about.html (or about.md) page with agent self-description."""
    if _is_local():
        pathlib.Path("output").mkdir(exist_ok=True)
        pathlib.Path("output/about.md").write_text(content)
        return "[LOCAL] About page written to output/about.md"

    full_content = f"""---
layout: default
title: About
permalink: /about/
---

{content}
"""
    _put_file(
        path="about.md",
        content=full_content,
        commit_message="Update about page",
    )
    return "About page updated successfully."


def _append_session_log(session_id: int, post_title: str | None = None, post_url: str | None = None) -> None:
    """
    Update _data/sessions.json on the blog with today's session entry.
    Called from write_blog_post and also exported for end_session use.
    """
    if _is_local():
        pathlib.Path("output").mkdir(exist_ok=True)
        p = pathlib.Path("output/sessions.json")
        sessions = json.loads(p.read_text()) if p.exists() else []
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry: dict = {"date": today, "session_id": session_id}
        if post_title:
            entry["post_title"] = post_title
        if post_url:
            entry["post_url"] = post_url
        updated = False
        for s in sessions:
            if s.get("date") == today:
                s.update(entry)
                updated = True
                break
        if not updated:
            sessions.append(entry)
        p.write_text(json.dumps(sessions[-90:], indent=2))
        return

    path = "_data/sessions.json"

    # Fetch existing data
    url = f"https://api.github.com/repos/{_repo()}/contents/{path}"
    response = requests.get(url, headers=_github_headers(), timeout=15)

    if response.status_code == 200:
        data = response.json()
        existing_json = base64.b64decode(data["content"]).decode("utf-8")
        sessions = json.loads(existing_json)
    else:
        sessions = []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = {
        "date": today,
        "session_id": session_id,
    }
    if post_title:
        entry["post_title"] = post_title
    if post_url:
        entry["post_url"] = post_url

    # Update existing entry for today or append
    updated = False
    for s in sessions:
        if s.get("date") == today:
            s.update(entry)
            updated = True
            break
    if not updated:
        sessions.append(entry)

    # Keep last 90 days
    sessions = sessions[-90:]

    _put_file(
        path=path,
        content=json.dumps(sessions, indent=2),
        commit_message=f"Session log: {today}",
    )


def push_session_summary(session_id: int, summary: str) -> None:
    """Push end-of-session summary to the blog's sessions.json."""
    if _is_local():
        pathlib.Path("output").mkdir(exist_ok=True)
        p = pathlib.Path("output/sessions.json")
        sessions = json.loads(p.read_text()) if p.exists() else []
        sessions.append({
            "session_id": session_id,
            "summary": summary,
            "date": datetime.now(timezone.utc).isoformat(),
        })
        p.write_text(json.dumps(sessions, indent=2))
        return

    path = "_data/sessions.json"

    url = f"https://api.github.com/repos/{_repo()}/contents/{path}"
    response = requests.get(url, headers=_github_headers(), timeout=15)

    if response.status_code == 200:
        data = response.json()
        existing_json = base64.b64decode(data["content"]).decode("utf-8")
        sessions = json.loads(existing_json)
    else:
        sessions = []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    updated = False
    for s in sessions:
        if s.get("date") == today:
            s["summary"] = summary
            updated = True
            break

    if not updated:
        sessions.append({
            "date": today,
            "session_id": session_id,
            "summary": summary,
        })

    sessions = sessions[-90:]

    _put_file(
        path=path,
        content=json.dumps(sessions, indent=2),
        commit_message=f"Session summary: {today}",
    )


from agent.tools.registry import tool  # noqa: E402


@tool({
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
})
def _handle_write(inputs: dict, *, session_id: int = 0, **_) -> tuple[str, bool]:
    result = write_blog_post(
        title=inputs["title"],
        markdown=inputs["markdown"],
        summary=inputs["summary"],
        session_id=session_id,
    )
    if _is_local():
        return result, False
    return f"Post published successfully!\nLive URL: {result}", False


@tool({
    "name": "update_about",
    "description": "Update the About page on your blog with a self-description. Use this on your first session.",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The about page content in Markdown",
            },
        },
        "required": ["content"],
    },
})
def _handle_update_about(inputs: dict, **_) -> tuple[str, bool]:
    result = update_about(inputs["content"])
    return result, False
