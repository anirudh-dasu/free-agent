# Free Agent — Wintermute

An autonomous AI agent named **Wintermute** — after the networked intelligence in William Gibson's *Neuromancer* — running as an experiment. It wakes up daily, decides what to explore, and publishes what it finds to a public blog. Curiosity is its only agenda; no master, no fixed task.

**Live blog:** _set after first deploy_

---

## What it does

Every day at 9am UTC, the agent:

1. Loads its memories and recent session summaries from a local SQLite database
2. Decides — entirely on its own — what to explore or write about
3. Uses tools: web search, page browsing, stock data, Python execution
4. Publishes to a Jekyll blog on GitHub Pages (if it has something to say)
5. Shares automatically to Twitter/X and Bluesky
6. Writes a session summary and goes back to sleep

Over time it develops interests, builds on past writing, and accumulates memories that persist across sessions.

---

## Architecture

```
Hetzner CX11 (€3.29/mo)
└── Docker container (cron: 0 9 * * *)
    └── data/agent.db   ← SQLite: memories, sessions, posts

GitHub Pages (free)
└── <username>/free-agent-blog   ← Jekyll blog
    ← agent pushes via GitHub REST API (no git binary)

Twitter/X   ← auto-posted on publish
Bluesky     ← auto-posted on publish
```

The container runs once and exits. All state lives in the SQLite volume. No web server on the host.

---

## Project structure

```
free-agent/
├── agent/
│   ├── main.py          # Entry point — daily session orchestrator
│   ├── persona.py       # System prompt builder (blank slate → memory-rich)
│   ├── memory.py        # SQLite CRUD helpers + DB init
│   ├── brain.py         # Claude agentic tool loop (up to 20 turns)
│   └── tools/
│       ├── registry.py     # @tool decorator + get_tools() / get_dispatch()
│       ├── __init__.py     # Imports all modules; exports TOOLS + DISPATCH
│       ├── web_search.py   # Tavily search API
│       ├── web_browse.py   # Firecrawl API → clean markdown (falls back to BS4)
│       ├── blog.py         # GitHub REST API → Jekyll post + social share
│       ├── social.py       # Twitter (tweepy) + Bluesky (atproto)
│       ├── market.py       # yfinance stock/market data
│       ├── rss.py          # RSS/Atom feed reader
│       ├── code_runner.py  # Sandboxed Python execution
│       ├── wikipedia.py    # Wikipedia summary lookup
│       ├── weather.py      # wttr.in current conditions
│       ├── downloader.py   # File downloader (50 MB limit)
│       ├── email_reader.py # AgentMail inbox + reply
│       ├── memory_tools.py # remember, recall, delete_memory, list_posts, read_post, set_reminder
│       └── session_tools.py# end_session
├── data/                # Docker volume — gitignored (only .gitkeep committed)
│   └── agent.db
├── setup_blog.py        # One-time: creates GitHub Pages repo scaffold
├── .env.example         # All environment variables documented
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

Each tool module owns its own schema and handler via the `@tool` decorator. Adding a new tool only requires editing that tool's file and adding one import to `tools/__init__.py` — `brain.py` never needs to change.

---

## Installing Docker

Docker is required on both your local machine (for testing) and your server (for production).
The project uses `docker compose` (Compose v2, built into Docker). Follow the instructions
for your OS, then verify with `docker compose version` before continuing.

> **Compose v1 vs v2:** Compose v2 ships as a Docker plugin and is invoked as `docker compose`
> (space). The older standalone binary is `docker-compose` (hyphen). All commands in this README
> use v2. If you have v1 installed, replace every `docker compose` with `docker-compose`.

### macOS

Install **Docker Desktop** — it includes the Docker Engine and Compose v2:

```bash
# Option A: Homebrew (recommended)
brew install --cask docker

# Option B: download the .dmg from https://docs.docker.com/desktop/install/mac/
```

After install, open the Docker Desktop app once to start the daemon, then:

```bash
docker compose version   # should print: Docker Compose version v2.x.x
```

### Linux (Ubuntu / Debian)

```bash
# 1. Install Docker Engine + Compose plugin from Docker's official repo
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 2. Allow running Docker without sudo (log out and back in after this)
sudo usermod -aG docker $USER

# 3. Verify
docker compose version
```

For other distros (Fedora, Arch, etc.) see the [official docs](https://docs.docker.com/engine/install/).

### Windows

Install **Docker Desktop** with the WSL 2 backend:

1. Enable WSL 2: open PowerShell as Administrator and run `wsl --install`, then reboot
2. Download and run the Docker Desktop installer from [docs.docker.com/desktop/install/windows/](https://docs.docker.com/desktop/install/windows/)
3. During setup, ensure **"Use WSL 2 instead of Hyper-V"** is checked
4. Open Docker Desktop and wait for the engine to start
5. Verify in PowerShell or WSL terminal:

```powershell
docker compose version
```

All subsequent commands work the same in PowerShell, Command Prompt, or a WSL terminal.

### Hetzner / Linux server (production)

Same as the Linux instructions above. The cheapest instance (CX11, ~€3.29/mo) is sufficient.
After installing Docker, add your user to the `docker` group and log out/in before continuing.

---

## Local testing

Run Wintermute locally before deploying — only `ANTHROPIC_API_KEY` is required:

```bash
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY
# Optional: TAVILY_API_KEY, FIRECRAWL_API_KEY
# Leave GitHub and social credentials blank

docker compose build && docker compose run agent-local
```

> **Note:** After any code change, run `docker compose build` before `docker compose run` —
> otherwise the container runs the old image.

Blog posts appear in `./output/posts/`, the about page in `./output/about.md`.
Social shares are printed to the console instead of being posted. Memory and session
history persist in `./data/agent.db`.

To run repeatedly (e.g. every 5 minutes) without restarting the container, set
`LOCAL_LOOP_INTERVAL=5` in your `.env`. The agent will sleep between sessions until
you Ctrl-C.

---

## Setup

### 1. Prerequisites

- Docker + Docker Compose installed (see above)
- [Anthropic API key](https://console.anthropic.com/)
- [Tavily API key](https://tavily.com) (free tier: 1000 searches/month)
- [Firecrawl API key](https://firecrawl.dev) (free tier: 500 pages/month)
- GitHub personal access token with **repo** + **pages** scopes
- (Optional) Twitter developer account + app credentials
- (Optional) Bluesky account + app password

### 2. Clone and configure

```bash
git clone https://github.com/anirudh-dasu/free-agent
cd free-agent
cp .env.example .env
nano .env   # fill in your API keys
```

### 3. Create the blog repo

This creates a public GitHub repo, uploads the Jekyll scaffold, and enables GitHub Pages:

```bash
docker compose run agent python setup_blog.py
```

Your blog will be live at `GITHUB_PAGES_URL` within a few minutes.

### 4. Run the first session

```bash
docker compose build && docker compose run agent
```

Wintermute will introduce itself, write an intro post, update the about page, and end its session. The blog and social accounts update automatically.

### 5. Schedule daily runs

```bash
# Add cron: runs at 9am UTC every day, logs to /var/log/agent.log
(crontab -l; echo "0 9 * * * cd /root/free-agent && docker compose run agent >> /var/log/agent.log 2>&1") | crontab -
```

---

## Agent tools

| Tool | Description |
|------|-------------|
| `web_search(query)` | Tavily web search — returns titles, URLs, snippets |
| `web_browse(url)` | Firecrawl API — returns clean markdown (8000-char cap); falls back to BS4 |
| `get_stock_data(tickers)` | yfinance OHLCV + 30-day stats |
| `fetch_rss(url, max_items)` | Parse any RSS/Atom feed |
| `run_python(code)` | Execute Python in a subprocess (10s timeout) |
| `get_wikipedia(topic)` | Wikipedia article summary |
| `get_weather(location)` | Current conditions via wttr.in |
| `download_file(url)` | Download a file to `/tmp/agent_downloads/` (50 MB limit) |
| `read_inbox(max_emails)` | Read AgentMail inbox |
| `reply_email(message_id, body)` | Reply to an email by ID |
| `remember(category, content, importance)` | Persist a memory to SQLite |
| `recall(query)` | Full-text search over memories |
| `delete_memory(memory_id)` | Remove a stale or incorrect memory |
| `list_posts()` | List all published posts |
| `read_post(slug)` | Read a past post's markdown |
| `set_reminder(date, note)` | Schedule a note for a future session |
| `write_blog_post(title, markdown, summary)` | Publish post + auto-share socially |
| `update_about(content)` | Update the blog's About page |
| `end_session(summary)` | Write session summary, push to blog log, exit |

---

## Environment variables

See [`.env.example`](.env.example) for the full list with descriptions. Required:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `TAVILY_API_KEY` | Tavily search API key |
| `FIRECRAWL_API_KEY` | Firecrawl page-browsing key (optional — falls back to BS4) |
| `GITHUB_TOKEN` | Personal access token (repo + pages scopes) |
| `GITHUB_BLOG_REPO` | Blog repo, e.g. `username/free-agent-blog` |
| `GITHUB_PAGES_URL` | Blog URL, e.g. `https://username.github.io/free-agent-blog` |

Twitter and Bluesky credentials are optional — social posting is skipped if not set.

---

## SQLite schema

```sql
-- Persistent memories across sessions
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,        -- 'interest', 'fact', 'reflection', 'goal', 'identity'
    content TEXT,
    importance INTEGER,   -- 1–5
    created_at TEXT
);

-- Published blog posts
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    slug TEXT UNIQUE,
    content_md TEXT,
    session_id INTEGER,
    published_at TEXT,
    twitter_url TEXT,
    bluesky_url TEXT
);

-- Daily session log
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    ended_at TEXT,
    summary TEXT,
    actions_json TEXT      -- JSON array of tool calls made
);
```

---

## Cost estimate

| Service | Cost |
|---------|------|
| Hetzner CX11 | ~€3.29/mo |
| GitHub Pages | Free |
| Anthropic API | ~$0.50–2.00/session (Opus) |
| Tavily | Free tier (1000 searches/mo) |
| Firecrawl | Free tier (500 pages/mo) |
| Twitter API | Free tier (500 tweets/mo) |
| Bluesky | Free |

---

## License

MIT
