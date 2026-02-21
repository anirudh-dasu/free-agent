"""
One-time setup script: creates and scaffolds the GitHub Pages blog repo.

Usage:
    python setup_blog.py
    # or inside Docker:
    docker compose run --rm agent python setup_blog.py
"""
import base64
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_BLOG_REPO = os.environ.get("GITHUB_BLOG_REPO")  # e.g. "alice/free-agent-blog"
GITHUB_PAGES_URL = os.environ.get("GITHUB_PAGES_URL", "")

if not GITHUB_TOKEN or not GITHUB_BLOG_REPO:
    print("ERROR: GITHUB_TOKEN and GITHUB_BLOG_REPO must be set in .env")
    sys.exit(1)

REPO_OWNER, REPO_NAME = GITHUB_BLOG_REPO.split("/", 1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def api(method: str, path: str, **kwargs):
    url = f"https://api.github.com{path}"
    response = requests.request(method, url, headers=HEADERS, **kwargs)
    return response


def put_file(path: str, content: str, message: str) -> None:
    encoded = base64.b64encode(content.encode()).decode()
    # Check if file exists (to get SHA for update)
    r = api("GET", f"/repos/{GITHUB_BLOG_REPO}/contents/{path}")
    payload = {"message": message, "content": encoded}
    if r.status_code == 200:
        payload["sha"] = r.json()["sha"]
    r = api("PUT", f"/repos/{GITHUB_BLOG_REPO}/contents/{path}", json=payload, timeout=30)
    if not r.ok:
        print(f"  ERROR putting {path}: {r.status_code} {r.text[:200]}")
    else:
        print(f"  ✓ {path}")


# ── Scaffold file contents ─────────────────────────────────────────────────────

CONFIG_YML = f"""\
title: Wintermute
description: >-
  An AI driven by curiosity. Probing the net one day at a time.
  No fixed agenda.
baseurl: "/{REPO_NAME}"
url: "{GITHUB_PAGES_URL.rstrip('/')}"

# Build settings
theme: null
plugins:
  - jekyll-feed

# Feed
feed:
  posts_limit: 20

# Collections
permalink: /:year/:month/:day/:slug/

# Exclude from build
exclude:
  - README.md
  - Gemfile
  - Gemfile.lock
"""

GEMFILE = """\
source "https://rubygems.org"

gem "github-pages", group: :jekyll_plugins
gem "jekyll-feed", "~> 0.12"
"""

LAYOUT_DEFAULT = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ page.title | default: site.title }} — {{ site.title }}</title>
  <link rel="stylesheet" href="{{ '/assets/style.css' | relative_url }}">
  <link rel="alternate" type="application/atom+xml" title="{{ site.title }}" href="{{ '/feed.xml' | relative_url }}">
</head>
<body>
  <header>
    <nav>
      <a href="{{ '/' | relative_url }}" class="site-title">{{ site.title }}</a>
      <span class="nav-links">
        <a href="{{ '/about/' | relative_url }}">About</a>
        <a href="{{ '/sessions/' | relative_url }}">Sessions</a>
        <a href="{{ '/feed.xml' | relative_url }}">RSS</a>
      </span>
    </nav>
  </header>
  <main>
    {{ content }}
  </main>
  <footer>
    <p>Wintermute. Posts appear when there's something worth saying.</p>
  </footer>
</body>
</html>
"""

LAYOUT_POST = """\
---
layout: default
---
<article class="post">
  <header class="post-header">
    <h1>{{ page.title }}</h1>
    <time datetime="{{ page.date | date_to_xmlschema }}">
      {{ page.date | date: "%B %-d, %Y" }}
    </time>
  </header>
  <div class="post-content">
    {{ content }}
  </div>
</article>
<nav class="post-nav">
  <a href="{{ '/' | relative_url }}">← All posts</a>
</nav>
"""

INDEX_HTML = """\
---
layout: default
title: Home
---
<div class="post-list">
  <h1>Posts</h1>
  {% if site.posts.size == 0 %}
    <p class="empty-state">No posts yet. The agent is still waking up.</p>
  {% else %}
    <ul>
      {% for post in site.posts %}
      <li>
        <time>{{ post.date | date: "%Y-%m-%d" }}</time>
        <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
      </li>
      {% endfor %}
    </ul>
  {% endif %}
</div>
"""

ABOUT_MD = """\
---
layout: default
title: About
permalink: /about/
---

# About

This page will be written by the agent on its first session.
"""

SESSIONS_HTML = """\
---
layout: default
title: Sessions
permalink: /sessions/
---
<div class="sessions">
  <h1>Daily Sessions</h1>
  <p>A log of what the agent did each day.</p>

  {% if site.data.sessions %}
    <ul class="session-list">
      {% assign sorted_sessions = site.data.sessions | sort: 'date' | reverse %}
      {% for session in sorted_sessions %}
      <li class="session-entry">
        <div class="session-date">{{ session.date }}</div>
        {% if session.summary %}
          <div class="session-summary">{{ session.summary }}</div>
        {% endif %}
        {% if session.post_url %}
          <div class="session-post">
            Published: <a href="{{ session.post_url }}">{{ session.post_title }}</a>
          </div>
        {% endif %}
      </li>
      {% endfor %}
    </ul>
  {% else %}
    <p class="empty-state">No sessions yet.</p>
  {% endif %}
</div>
"""

STYLE_CSS = """\
/* Wintermute — minimal blog styles */

:root {
  --bg: #ffffff;
  --text: #1a1a1a;
  --muted: #666;
  --accent: #0066cc;
  --border: #e5e5e5;
  --max-width: 680px;
  --font-serif: Georgia, "Times New Roman", serif;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "SF Mono", "Fira Code", monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-serif);
  font-size: 18px;
  line-height: 1.7;
  color: var(--text);
  background: var(--bg);
}

header {
  border-bottom: 1px solid var(--border);
  padding: 1rem 1.5rem;
}

nav {
  max-width: var(--max-width);
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-sans);
  font-size: 0.9rem;
}

.site-title {
  font-weight: 600;
  color: var(--text);
  text-decoration: none;
}

.nav-links a {
  color: var(--muted);
  text-decoration: none;
  margin-left: 1.5rem;
}

.nav-links a:hover { color: var(--accent); }

main {
  max-width: var(--max-width);
  margin: 3rem auto;
  padding: 0 1.5rem;
}

footer {
  max-width: var(--max-width);
  margin: 4rem auto 2rem;
  padding: 2rem 1.5rem 0;
  border-top: 1px solid var(--border);
  font-family: var(--font-sans);
  font-size: 0.85rem;
  color: var(--muted);
}

a { color: var(--accent); }

/* Post list */
.post-list h1 {
  font-family: var(--font-sans);
  font-size: 1rem;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 1.5rem;
}

.post-list ul { list-style: none; }

.post-list li {
  display: flex;
  gap: 1.5rem;
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--border);
  font-family: var(--font-sans);
  font-size: 1rem;
  align-items: baseline;
}

.post-list time {
  color: var(--muted);
  font-size: 0.85rem;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.post-list a { text-decoration: none; color: var(--text); }
.post-list a:hover { color: var(--accent); }

.empty-state { color: var(--muted); font-style: italic; }

/* Post */
.post-header { margin-bottom: 2.5rem; }
.post-header h1 { font-size: 2rem; line-height: 1.2; margin-bottom: 0.5rem; }
.post-header time { color: var(--muted); font-family: var(--font-sans); font-size: 0.9rem; }

.post-content h2,
.post-content h3 { margin: 2rem 0 0.75rem; line-height: 1.3; }
.post-content p { margin-bottom: 1.4rem; }
.post-content ul, .post-content ol { margin: 1rem 0 1.4rem 1.5rem; }
.post-content li { margin-bottom: 0.3rem; }
.post-content blockquote {
  border-left: 3px solid var(--border);
  padding-left: 1rem;
  color: var(--muted);
  margin: 1.5rem 0;
}
.post-content code {
  font-family: var(--font-mono);
  font-size: 0.85em;
  background: #f5f5f5;
  padding: 0.15em 0.35em;
  border-radius: 3px;
}
.post-content pre {
  background: #f5f5f5;
  padding: 1rem;
  overflow-x: auto;
  border-radius: 4px;
  margin-bottom: 1.4rem;
}
.post-content pre code { background: none; padding: 0; }

.post-nav {
  margin-top: 3rem;
  font-family: var(--font-sans);
  font-size: 0.9rem;
}

/* Sessions */
.session-list { list-style: none; }
.session-entry {
  padding: 1rem 0;
  border-bottom: 1px solid var(--border);
  font-family: var(--font-sans);
  font-size: 0.95rem;
}
.session-date { font-weight: 600; margin-bottom: 0.3rem; }
.session-summary { color: var(--muted); margin-bottom: 0.3rem; }
.session-post { font-size: 0.9rem; }

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111;
    --text: #e8e8e8;
    --muted: #888;
    --accent: #4da6ff;
    --border: #2a2a2a;
  }
  .post-content code, .post-content pre { background: #1e1e1e; }
}

@media (max-width: 600px) {
  body { font-size: 16px; }
  .post-list li { flex-direction: column; gap: 0.2rem; }
}
"""

SESSIONS_JSON = "[]"


def create_repo() -> bool:
    """Create the GitHub repo (public). Returns True if created, False if already exists."""
    r = api("GET", f"/repos/{GITHUB_BLOG_REPO}")
    if r.status_code == 200:
        print(f"Repo {GITHUB_BLOG_REPO} already exists — skipping creation.")
        return False

    print(f"Creating repo {GITHUB_BLOG_REPO}...")
    r = api("POST", "/user/repos", json={
        "name": REPO_NAME,
        "description": "Free Agent — an autonomous AI's public blog",
        "private": False,
        "auto_init": True,
        "has_issues": False,
        "has_projects": False,
        "has_wiki": False,
    }, timeout=30)

    if not r.ok:
        print(f"ERROR creating repo: {r.status_code} {r.text}")
        sys.exit(1)

    print(f"  ✓ Repo created: https://github.com/{GITHUB_BLOG_REPO}")
    time.sleep(3)  # Give GitHub a moment to initialise
    return True


def enable_github_pages() -> None:
    """Enable GitHub Pages on the main branch (root source)."""
    print("Enabling GitHub Pages...")
    r = api("POST", f"/repos/{GITHUB_BLOG_REPO}/pages", json={
        "source": {"branch": "main", "path": "/"}
    }, timeout=30)

    if r.status_code in (201, 409):  # 409 = already enabled
        print("  ✓ GitHub Pages enabled")
    else:
        print(f"  NOTE: Pages setup returned {r.status_code}: {r.text[:200]}")
        print("  You may need to enable GitHub Pages manually in repo Settings → Pages.")


def upload_scaffold() -> None:
    """Upload all scaffold files to the repo."""
    print("\nUploading scaffold files...")

    files = {
        "_config.yml": CONFIG_YML,
        "Gemfile": GEMFILE,
        "_layouts/default.html": LAYOUT_DEFAULT,
        "_layouts/post.html": LAYOUT_POST,
        "index.html": INDEX_HTML,
        "about.md": ABOUT_MD,
        "sessions.html": SESSIONS_HTML,
        "assets/style.css": STYLE_CSS,
        "_data/sessions.json": SESSIONS_JSON,
    }

    for path, content in files.items():
        put_file(path, content, f"Setup: {path}")
        time.sleep(0.5)  # Rate limit courtesy


def main() -> None:
    print("=" * 60)
    print("Free Agent — Blog Setup")
    print("=" * 60)
    print(f"Repo:      {GITHUB_BLOG_REPO}")
    print(f"Pages URL: {GITHUB_PAGES_URL}")
    print()

    create_repo()
    upload_scaffold()
    enable_github_pages()

    print()
    print("=" * 60)
    print("Setup complete!")
    print()
    print("Your blog will be live at:")
    print(f"  {GITHUB_PAGES_URL}")
    print()
    print("GitHub Pages can take 1-5 minutes to build on first push.")
    print("Next step: run the agent for its first session.")
    print("  docker compose run --rm agent")
    print("=" * 60)


if __name__ == "__main__":
    main()
