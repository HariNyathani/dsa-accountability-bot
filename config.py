"""
Configuration loader — reads .env and exposes bot-level settings.

User-specific settings (channel, deadline, reminders, timezone) are stored
in the database per user, NOT here.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _safe_int(key: str, default: str = "0") -> int:
    """Safely parse an integer from env, returning 0 on failure."""
    val = os.getenv(key, default)
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


# ── Discord (bot-level) ─────────────────────────────────────────────────────
DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
ADMIN_CHANNEL_ID: int = _safe_int("ADMIN_CHANNEL_ID")
BOT_OWNER_ID: int = _safe_int("BOT_OWNER_ID")  # optional: restrict admin commands

# ── Email (Gmail SMTP — bot-level credentials) ──────────────────────────────
GMAIL_ADDRESS: str = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")

# ── Default timezone (used for new users) ────────────────────────────────────
DEFAULT_TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")

# ── AI (optional) ───────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "db/dsa_bot.db")
