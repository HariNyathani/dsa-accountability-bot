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
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost/dsa_bot")

# ── API Server ───────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = _safe_int("API_PORT", "8000")

# ── Discord OAuth2 ───────────────────────────────────────────────────────
DISCORD_CLIENT_ID: str = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET: str = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_OAUTH_REDIRECT_URI: str = os.getenv(
    "DISCORD_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback"
)

# ── Session / JWT ────────────────────────────────────────────────────────
SESSION_SECRET: str = os.getenv("SESSION_SECRET", "change-me-to-a-random-secret-key")
COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# ── Frontend ─────────────────────────────────────────────────────────────
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ── Legacy / compat ──────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
