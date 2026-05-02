# Multi-User DSA Bot — Implementation Plan

## Overview
Convert the existing single-user DSA Accountability Bot into a multi-user system where any Discord user can self-register, configure their own tracking channel/reminders/timezone, and compete on a group leaderboard.

---

## Phase 1: Database Schema Refactor
**Files:** `db/database.py`, `config.py`

### New/Modified Tables

| Table | Purpose |
|---|---|
| `users` | Extended with `timezone`, `is_active` columns |
| `user_settings` | **NEW** — per-user tracked channel, deadline, reminder times |
| `progress_logs` | No schema change needed (already per-user) |
| `daily_status` | Rename reminder columns to generic `warn_sent`, `final_sent`, `email_sent` |
| `streaks` | No schema change needed |
| `weekly_summaries` | No schema change needed |

### Key Changes
- Add `user_settings` table with: `tracked_channel_id`, `deadline_hour`, `deadline_minute`, `warn_hour`, `warn_minute`, `final_hour`, `final_minute`, `email_hour`, `email_minute`, `is_active`
- Add migration logic to preserve existing data
- Add new DB helper functions: `get_all_active_users()`, `get_user_settings()`, `update_user_settings()`, `get_users_for_channel()`, `register_user()`, `unregister_user()`

---

## Phase 2: Config Simplification
**Files:** `config.py`, `.env`, `.env.example`

- Remove user-specific variables from config: `DISCORD_USER_ID`, `DSA_CHANNEL_ID`, `REMINDER_*` times
- Keep only bot-level secrets: `DISCORD_BOT_TOKEN`, `GMAIL_*`, `OPENAI_API_KEY`, `DATABASE_PATH`
- Keep `TIMEZONE` as a default timezone for new users
- Keep `ADMIN_CHANNEL_ID` for bot admin channel

---

## Phase 3: Message Handler → Multi-User
**Files:** `handlers/message_handler.py`

- Remove hardcoded `config.DISCORD_USER_ID` / `config.DSA_CHANNEL_ID` checks
- On each message: query DB for any registered user whose `tracked_channel_id` matches `message.channel.id` AND whose `discord_user_id` matches `message.author.id`
- If match found → log progress for that user
- If no match → ignore silently

---

## Phase 4: Reminder Handler → Per-User
**Files:** `handlers/reminder_handler.py`, `bot.py`

- Replace 3 fixed cron jobs with a single **minutely ticker** that runs every minute
- Each tick: query all active users, check if current time matches any user's reminder schedule (in their timezone)
- Send DM/email to only the users who need it, respecting `daily_status` flags

---

## Phase 5: Summary Handler → Per-User
**Files:** `handlers/summary_handler.py`

- `generate_weekly_summary()` iterates over all active users
- Each user gets their own summary based on their own data
- `get_status_report()` / `get_topic_summary()` already take `user_id` — just remove the hardcoded user from callers

---

## Phase 6: Bot Commands Refactor
**Files:** `bot.py`

### Self-Service Commands (any user)
| Command | Action |
|---|---|
| `!register` / `!setup` | Register the calling user, create DB records with defaults |
| `!unregister` | Deactivate user |
| `!setchannel <#channel>` | Set tracked channel (supports mention or ID) |
| `!setemail <email>` | Set reminder email |
| `!setdeadline <HH:MM>` | Set deadline time |
| `!setreminders <warn,final,email>` | Set reminder times |
| `!settimezone <tz>` | Set user timezone |
| `!mysettings` | Show current config |
| `!resetconfig` | Reset to defaults |
| `!status` | Per-user status |
| `!streak` | Per-user streak |
| `!weekly` | Per-user weekly summary |
| `!topics` | Per-user topic analysis |
| `!exportcsv` | Per-user CSV export |
| `!insights` / `!analyze` | Per-user AI analysis |
| `!leaderboard [sort]` | Group leaderboard |
| `!help` | Updated help |

### Admin Commands (bot owner only)
| Command | Action |
|---|---|
| `!admin users` | List all registered users |
| `!admin missed` | Show who missed today |
| `!forcesummary` | Force weekly summary for all users |

---

## Phase 7: Leaderboard Feature
**Files:** `handlers/leaderboard_handler.py` (NEW)

- Query all active users' streaks, consistency, total posts
- Sort by requested metric (default: current streak)
- Build a rich embed with rankings, medals, and stats

---

## Phase 8: AI Insights Per User
**Files:** `services/ai_service.py`

- Add `!insights` command that generates personalized AI analysis
- Already mostly per-user, just needs a command trigger

---

## Phase 9: Email Service Per User
**Files:** `services/email_service.py`

- `send_reminder_email()` now takes a `to_email` parameter from user settings
- Falls back to global config if user has no email set

---

## Build Order
1. Database schema + migration
2. Config simplification
3. Message handler multi-user
4. Reminder handler per-user scheduling
5. Bot commands refactor (register, settings, existing commands)
6. Leaderboard
7. Weekly summary per-user
8. AI insights command
9. Testing & polish
