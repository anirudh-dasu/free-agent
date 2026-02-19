"""
Blog publishing via GitHub REST API → GitHub Pages (Jekyll).
"""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone

import requests

from agent.tools.social import share_post
from agent import memory as mem


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
    full_content = front_matter + "\n" + markdown

    _put_file(
        path=filename,
        content=full_content,
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


def update_about(content: str) -> None:
    """Update the about.html (or about.md) page with agent self-description."""
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


def _append_session_log(session_id: int, post_title: str | None = None, post_url: str | None = None) -> None:
    """
    Update _data/sessions.json on the blog with today's session entry.
    Called from write_blog_post and also exported for end_session use.
    """
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
