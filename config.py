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
BOT_OWNER_ID: int = _safe_int("BOT_OWNER_ID")  # primary owner — full bot-admin access

# P3-08: Optional comma-separated list of Discord user IDs who share bot-owner
# trust level (co-admins).  These IDs may use !sudo_log and @user cross-user
# commands just like BOT_OWNER_ID.  Guild "Administrator" permission is never
# sufficient — use this allowlist for intentional elevation only.
# Example: BOT_OWNER_ALLOWLIST="123456789012345678,987654321098765432"
# (Read at runtime in bot.py:_is_bot_owner — no reload needed.)

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
DISCORD_OAUTH_MOBILE_REDIRECT_URI: str = os.getenv(
    "DISCORD_OAUTH_MOBILE_REDIRECT_URI",
    DISCORD_OAUTH_REDIRECT_URI.replace("/callback", "/mobile-callback"),
)

# ── Session / JWT ────────────────────────────────────────────────────────
# SECURITY: SESSION_SECRET must be a strong, randomly generated value in
# production. Generating one: python -c "import secrets; print(secrets.token_hex(32))"
SESSION_SECRET: str = os.getenv("SESSION_SECRET", "")
COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# ── Environment ───────────────────────────────────────────────────────────
# Used by Module 10 (docs gating) and the secret strength check below.
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()

# Fail-fast secret strength check (P2-03 — JWT forgery via default secret)
_INSECURE_DEFAULTS = {"", "change-me-to-a-random-secret-key"}
if SESSION_SECRET in _INSECURE_DEFAULTS or len(SESSION_SECRET) < 32:
    if ENVIRONMENT in ("production", "prod"):
        raise RuntimeError(
            "SESSION_SECRET must be set to a random value >= 32 characters in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    else:
        import logging as _logging
        _logging.getLogger("dsa_bot.config").warning(
            "SESSION_SECRET is weak or unset — this is acceptable only in development. "
            "Set a strong SESSION_SECRET before deploying to production."
        )

# ── Frontend ─────────────────────────────────────────────────────────────
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ── Admin Panel ──────────────────────────────────────────────────────────
# The Discord user ID that has access to /admin/* API endpoints and the
# web admin panel. Stored as a string to match JWT session payload format.
# Falls back to BOT_OWNER_ID if not explicitly set.
ADMIN_DISCORD_ID: str = os.getenv("ADMIN_DISCORD_ID", str(BOT_OWNER_ID) if BOT_OWNER_ID else "")

# ── Legacy / compat ──────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
