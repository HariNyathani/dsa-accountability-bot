<div align="center">

# 🧠 DSA Accountability Platform

**A full-stack accountability system for serious DSA grinders.**  
Discord bot with custom NLP · FastAPI REST API · React Dashboard · LeetCode + Codeforces integration

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://supabase.com)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discordpy.readthedocs.io)

</div>

---

## What Is This?

Most people who want to build a DSA habit fail because there's zero friction to skip a day and zero visibility into what they're actually practicing.

This platform fixes that. It lives inside your Discord server. You post your progress naturally — the bot parses it, logs it, tracks your streak, and sends escalating reminders if you haven't posted by your deadline. A web dashboard gives you a full picture of your consistency, difficulty distribution, and topic coverage over time.

**The key engineering insight:** the bot understands natural language. You don't fill out a form. You just type what you did.

---

## Features

### 🤖 Discord Bot
- **Natural language parsing** — type "solved Two Sum and 3 graph problems today" and it extracts topics, counts problems, and logs everything automatically
- **`!qn <id>`** — instant lookup by problem ID for both platforms:
  - `!qn 73` → *Set Matrix Zeroes \[Medium\]* (LeetCode)
  - `!qn 4A` → *Watermelon \[Easy\]* (Codeforces)
  - `!qn 2211B` → *Xor Product \[Expert\]* (Codeforces)
- **`!qdone`** — batch logging: `!qdone dp 3 hard, trees 2, graphs 1 medium`
- **`!log <url>`** — paste any LeetCode or Codeforces URL to log it directly
- **Streak tracking** with current and longest streak, motivational milestones
- **Difficulty distribution** with Unicode bar charts (Easy / Medium / Hard / Expert)
- **Topic frequency analysis** — see what you're over/under-practicing
- **Leaderboard** — sortable by streak, consistency, total posts, or longest streak
- **Weekly auto-summaries** — generated every Monday, sent to each user's DM or channel
- **Multi-tier reminder system** — warn → final → email escalation with per-user deadlines
- **Rest day tracking** — `!rest` logs a rest day (capped at 4/month), preserves your streak
- **AI study insights** — powered by Google Gemini (optional), analyzes your logs and gives personalized coaching
- **CSV export** — `!exportcsv` dumps your full progress history as a file attachment
- **Admin suite** — `!admin users`, `!admin missed`, `!admin forcesummary`
- **Per-user configuration** — timezone, channel, deadline, reminder times, email

### 🌐 Web Dashboard (React)
- **GitHub-style activity heatmap** — 365-day view with intensity scaling and tooltips
- **Personal dashboard** — streak, total problems, consistency %, recent activity
- **Analytics page** — topic distribution chart, difficulty breakdown (Recharts)
- **User profile editor** — update email, timezone, reminder settings live
- **Leaderboard page** — full group ranking
- **Discord OAuth2 login** — no passwords, sign in with your Discord account

### ⚙️ REST API (FastAPI)
- 8 route modules: `auth`, `users`, `progress`, `analytics`, `leaderboard`, `summaries`, `reminders`, `health`
- JWT authentication with role-based access control
- Pydantic v2 schema validation
- Centralized error handling and request logging middleware
- Deep health check endpoint with DB latency reporting

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Discord Server                           │
│   User types progress → Bot reads message → NLP Pipeline       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Discord Bot (bot.py)  │
              │   discord.py + APSched  │
              └────────────┬────────────┘
                           │
         ┌─────────────────▼──────────────────┐
         │         Progress Service            │
         │  4-Stage NLP Parsing Pipeline       │
         │  ① Classify  ② Bullet Parser        │
         │  ③ Keywords  ④ LC Fuzzy Fallback    │
         └──────┬──────────────┬───────────────┘
                │              │
    ┌───────────▼──┐    ┌──────▼───────────────┐
    │  Resolver    │    │   PostgreSQL (async)  │
    │  Registry    │    │   psycopg2 pool       │
    │  LeetCode ─┐ │    │   6 tables + JSONB    │
    │  Codeforces┘ │    └──────────┬────────────┘
    └───────────┬──┘               │
                │                  │
    ┌───────────▼──────────────────▼────────────┐
    │           FastAPI REST API                 │
    │        (JWT Auth · 8 route modules)        │
    └──────────────────┬────────────────────────┘
                       │
          ┌────────────▼─────────────┐
          │   React Dashboard        │
          │   Vite · TypeScript      │
          │   Recharts · Heatmap     │
          └──────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Discord Bot** | Python 3.11+, discord.py 2.3+, APScheduler |
| **NLP / Parsing** | Custom pipeline, RapidFuzz (fuzzy matching), regex |
| **REST API** | FastAPI, Uvicorn, Pydantic v2 |
| **Authentication** | Discord OAuth2, python-jose (JWT), httpx |
| **Database** | PostgreSQL via Supabase, psycopg2, async connection pool |
| **External APIs** | LeetCode GraphQL API, Codeforces REST API |
| **Email** | Gmail SMTP (smtplib, built-in) |
| **AI** | Google Gemini (optional, `google-generativeai`) |
| **Frontend** | React 19, TypeScript 5.8, Vite 6 |
| **Charts** | Recharts 2 |
| **Data Export** | pandas |
| **Testing** | pytest, pytest-asyncio |
| **Deployment** | Render (bot + API), Supabase (DB) |

---

## Project Structure

```
dsa-accountability-bot/
├── bot.py                    # Discord bot entry point (20+ commands, scheduler)
├── main.py                   # Unified startup (bot + API together)
├── config.py                 # Centralized config loader
├── init_postgres.sql         # Database schema (6 tables)
│
├── api/                      # FastAPI REST API
│   ├── app.py                # App factory, CORS, middleware registration
│   ├── routes/               # 8 route modules
│   │   ├── auth.py           # Discord OAuth2, JWT login/refresh
│   │   ├── users.py          # User CRUD, settings, email, timezone
│   │   ├── progress.py       # Log submission, history, undo
│   │   ├── analytics.py      # Topic/difficulty/heatmap data
│   │   ├── leaderboard.py    # Group rankings
│   │   ├── summaries.py      # Weekly summaries
│   │   ├── reminders.py      # Reminder config
│   │   └── health.py         # Deep health check
│   ├── schemas/              # Pydantic v2 request/response models
│   └── middleware/           # Auth, error handling, request logging
│
├── services/
│   ├── progress_service.py   # ★ Core NLP parsing pipeline (647 lines)
│   ├── ai_service.py         # Gemini AI insights
│   ├── email_service.py      # SMTP reminder emails
│   ├── discord_service.py    # Discord API helpers
│   └── export_service.py     # CSV generation
│
├── handlers/
│   ├── message_handler.py    # Routes Discord messages to the pipeline
│   ├── reminder_handler.py   # Per-user scheduled reminders
│   ├── summary_handler.py    # Weekly summary generation
│   └── leaderboard_handler.py
│
├── db/
│   └── database.py           # Async PostgreSQL ORM (729 lines)
│
├── utils/
│   ├── topic_extractor.py    # Keyword + alias NLP extraction
│   ├── command_parser.py     # !qdone argument parser
│   ├── streak_utils.py       # Streak calculation engine
│   ├── time_utils.py         # Timezone-aware date helpers
│   ├── matcher.py            # Fuzzy match entry point
│   └── resolvers/            # ★ Multi-platform problem resolver
│       ├── __init__.py       # Registry + resolve_problem() entrypoint
│       ├── base.py           # Abstract resolver base class
│       ├── detector.py       # Platform auto-detection
│       ├── leetcode.py       # LeetCode GraphQL resolver
│       └── codeforces.py     # Codeforces REST resolver
│
├── scripts/
│   ├── sync_leetcode.py      # Fetch + cache full LeetCode problem set
│   └── sync_codeforces.py    # Fetch + normalize Codeforces problems
│
├── tests/
│   ├── test_api.py
│   ├── test_topic_extractor.py
│   └── test_time_utils.py
│
└── frontend/                 # React + TypeScript dashboard
    └── src/
        ├── pages/            # 7 pages (Dashboard, Analytics, Leaderboard, ...)
        ├── components/       # 8 components (Heatmap, QuickLogCard, ...)
        ├── services/api.ts   # Typed API client
        ├── contexts/         # Auth context (Discord OAuth state)
        ├── hooks/            # useApi custom hook
        ├── types/index.ts    # Full TypeScript type definitions
        └── index.css         # Design system (tokens, animations, glassmorphism)
```

---

## Bot Commands Reference

### Registration & Setup
| Command | Description |
|---|---|
| `!register` | Register yourself for DSA tracking |
| `!unregister` | Deactivate tracking (data preserved) |
| `!setchannel #channel` | Set the channel the bot monitors |
| `!setemail you@email.com` | Set your reminder email |
| `!setdeadline HH:MM` | Set your daily deadline (e.g. `23:00`) |
| `!setreminders HH:MM,HH:MM,HH:MM` | Warn, final, and email reminder times |
| `!settimezone Asia/Kolkata` | Set your timezone |
| `!mysettings` | View your current configuration |
| `!resetconfig` | Reset all settings to defaults |

### Logging Progress
| Command | Description |
|---|---|
| Natural message | Just type in your tracked channel — the bot parses it |
| `!log <url or title>` | Log a specific problem by URL or full title |
| `!qn <id>` | Quick-log by problem ID (e.g. `!qn 73`, `!qn 4A`, `!qn 2211B`) |
| `!qdone <topic> [count] [diff], ...` | Batch-log: `!qdone dp 3 hard, trees 2` |
| `!rest` | Log a rest day (4 allowed per month, streak preserved) |
| `!undo` | Remove your most recent log entry |

### Stats & Reporting
| Command | Description |
|---|---|
| `!status` | Your today status, streak, consistency |
| `!streak` | Current and longest streak |
| `!topics` | Topic frequency ranking (top 10) |
| `!difficulty` | Difficulty distribution with bar charts |
| `!weekly` | Generate your weekly summary on demand |
| `!leaderboard [sort]` | Group leaderboard (`streak`, `consistency`, `posts`, `longest`) |
| `!exportcsv` | Download your full progress history as CSV |
| `!insights` | AI-powered coaching report (requires Gemini API key) |

### Admin Only
| Command | Description |
|---|---|
| `!admin users` | List all registered users |
| `!admin missed` | Show who hasn't posted today |
| `!admin forcesummary` | Trigger weekly summary for all users |
| Most commands support `@user` | e.g. `!register @user`, `!difficulty @user` |

---

## How the NLP Pipeline Works

When a message hits the bot that isn't a command, it flows through four stages:

```
Input: "Solved Two Sum today, also did 3 graph problems"

Stage 1 — CLASSIFY
  → intent: "done"

Stage 2 — BULLET PARSER (checks first)
  → No bullet structure detected, move on

Stage 3 — KEYWORD EXTRACTION
  → Scans with longest-match-first alias map
  → "graph" → canonical: "Graphs", count: 3

Stage 4 — LEETCODE FUZZY FALLBACK
  → "Solved Two Sum today" stripped of action verbs → "Two Sum"
  → RapidFuzz match against LeetCode DB → "Two Sum" [Easy] (score: 100)

Result: logs 1× Two Sum [Easy] + 3× Graphs
Feedback: "✅ Logged 1 question: Two Sum [Easy] (Auto-tagged: Arrays, Hash Table)
           ✅ Logged 3 questions: Graphs"
```

**Bullet-list messages** are also parsed with a header+item structure:
```
Graphs:
 - BFS on a grid
 - Dijkstra shortest path

DP:
 - Coin change
```
→ Logs 2 Graphs + 1 Dynamic Programming (each bullet = 1 problem).

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL database (or a [Supabase](https://supabase.com) project — free tier works)
- A Discord application with a bot token and OAuth2 credentials

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/dsa-accountability-bot.git
cd dsa-accountability-bot
```

### 2. Set up Python environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your values (see Environment Variables section below)
```

### 4. Initialize the database
```bash
# The bot runs init_postgres.sql automatically on startup.
# Or run it manually against your PostgreSQL instance:
psql $DATABASE_URL -f init_postgres.sql
```

### 5. Sync problem databases (one-time)
```bash
# Download and cache the full LeetCode problem set for fuzzy matching
python scripts/sync_leetcode.py

# Download and cache Codeforces problems
python scripts/sync_codeforces.py
```

### 6. Start the bot + API
```bash
python main.py
```

### 7. Set up the frontend
```bash
cd frontend
cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000

npm install
npm run dev
# Dashboard runs at http://localhost:5173
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the following:

```env
# ── Discord Bot ───────────────────────────────────────────────────
DISCORD_BOT_TOKEN=           # From discord.com/developers/applications
BOT_OWNER_ID=                # Your Discord user ID (for admin commands)
ADMIN_CHANNEL_ID=            # Optional: private channel for bot alerts

# ── Database ──────────────────────────────────────────────────────
DATABASE_URL=postgresql://user:password@host:5432/dbname

# ── Discord OAuth2 (Dashboard Login) ─────────────────────────────
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
DISCORD_OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback

# ── JWT Session ───────────────────────────────────────────────────
SESSION_SECRET=              # Generate: python -c "import secrets; print(secrets.token_hex(32))"

# ── Email Reminders ───────────────────────────────────────────────
GMAIL_ADDRESS=               # Gmail address for sending reminders
GMAIL_APP_PASSWORD=          # Gmail App Password (not your login password)

# ── Optional ──────────────────────────────────────────────────────
GEMINI_API_KEY=              # Google Gemini API key for !insights command
TIMEZONE=Asia/Kolkata        # Default timezone for new users
FRONTEND_URL=http://localhost:5173
```

---

## Deployment

### Render (Recommended — Free Tier)
A `render.yaml` is included. Connect your GitHub repo to [Render](https://render.com), and it will auto-deploy the bot + API as a background worker.

Set all environment variables in the Render dashboard under **Environment**.

### Frontend
Deploy the `frontend/` directory to [Vercel](https://vercel.com) or [Netlify](https://netlify.com):
```bash
cd frontend
npm run build
# Deploy the dist/ folder
```
Set `VITE_API_URL` to your Render API URL.

### Database
Use [Supabase](https://supabase.com) free tier. Create a project, grab the `DATABASE_URL` from **Settings → Database**, and run `init_postgres.sql` in the SQL editor.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests cover the REST API endpoints, topic extractor NLP logic, and timezone utilities.

---

## Database Schema

Six PostgreSQL tables:

| Table | Purpose |
|---|---|
| `users` | User registry (Discord ID, username, email, timezone, active flag) |
| `user_settings` | Per-user reminder times, deadline, tracked channel |
| `progress_logs` | Every logged entry with full message content, parsed JSONB, platform |
| `daily_status` | Posted flag + reminder-sent flags per user per day |
| `streaks` | Current streak, longest streak, last post date |
| `weekly_summaries` | Archived weekly reports |

Log entries store structured data as PostgreSQL JSONB, enabling efficient per-problem queries without schema migrations when the log format evolves.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run the test suite: `pytest tests/ -v`
4. Open a Pull Request

For major changes, open an issue first to discuss the approach.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built to make the DSA grind unavoidable. 💀
</div>
