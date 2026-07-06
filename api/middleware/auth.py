"""
JWT session utilities for Discord OAuth2 authentication.

╔══════════════════════════════════════════════════════════════════════════╗
║  SECURITY DECISION — BEARER-ONLY AUTH (Module 9 / P2-04)               ║
║                                                                          ║
║  Auth transport: Authorization: Bearer <token> ONLY.                    ║
║  Cookies are NOT an accepted credential transport.                       ║
║                                                                          ║
║  Rationale: The Flutter mobile app (and web dashboard) authenticate      ║
║  strictly via the Authorization header. Bearer tokens live in            ║
║  app-controlled storage and are NEVER auto-attached by a browser,        ║
║  so cross-site requests cannot carry them — CSRF is not an applicable    ║
║  threat vector for this architecture.                                    ║
║                                                                          ║
║  ⚠ DO NOT add cookie auth without re-introducing CSRF protection.       ║
║    The moment a session credential is stored in a cookie, the CSRF      ║
║    assumption breaks and the entire threat model must be revisited.      ║
║                                                                          ║
║  The one browser-facing leg — the OAuth login redirect — is protected   ║
║  against login-CSRF by the `state` parameter (Module 4 / P2-11).        ║
║  The state is stored in a short-lived HttpOnly cookie for the duration   ║
║  of the redirect only; it carries no session credential.                 ║
╚══════════════════════════════════════════════════════════════════════════╝

Security decisions (Module 4):
  - Token TTL: ACCESS_TOKEN_TTL_HOURS env var, default 24 h (was 30 days).
  - jti claim: unique token ID minted per token; stored in revoked_tokens on
    logout so compromised tokens can be invalidated before expiry.
  - Revocation: every decode call synchronously checks revoked_tokens. The
    check uses the existing _sync/_run_sync pattern (no Redis required).
"""

import logging
import os as _os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from jose import JWTError, jwt
from fastapi import Request
from pydantic import BaseModel

import config
from db import database

logger = logging.getLogger("dsa_bot.api.auth")

ALGORITHM = "HS256"

# Configurable token lifetime — default 24 hours. Override via env:
#   ACCESS_TOKEN_TTL_HOURS=168   # 7 days, if longer sessions are needed
TOKEN_EXPIRE_SECONDS = int(_os.getenv("ACCESS_TOKEN_TTL_HOURS", "24")) * 3600

_BEARER_PREFIX = "Bearer "


class SessionUser(BaseModel):
    """Decoded JWT payload representing the logged-in Discord user."""
    id: str
    username: str
    avatar: Optional[str] = None
    discriminator: str = "0"
    jti: Optional[str] = None  # carried so logout can revoke the exact token


def create_session_token(user: dict) -> str:
    """Create a signed JWT from Discord user info.

    Claims added (Module 4):
      - jti: unique token identifier for revocation.
      - iat: issued-at timestamp.
      - exp: now + TOKEN_EXPIRE_SECONDS (default 24 h).
    """
    now = int(time.time())
    payload = {
        "sub": str(user["id"]),
        "username": user.get("username", ""),
        "avatar": user.get("avatar"),
        "discriminator": user.get("discriminator", "0"),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, config.SESSION_SECRET, algorithm=ALGORITHM)


# ── Revocation helpers (sync DB, run in thread) ──────────────────────────────

def _is_revoked_sync(jti: str) -> bool:
    """Return True if the jti exists in revoked_tokens (blocking)."""
    with database.db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM revoked_tokens WHERE jti = %s LIMIT 1",
                (jti,),
            )
            return cur.fetchone() is not None


def _revoke_token_sync(jti: str) -> None:
    """Insert jti into revoked_tokens (blocking). No-op if already revoked."""
    with database.db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO revoked_tokens (jti)
                VALUES (%s)
                ON CONFLICT (jti) DO NOTHING
                """,
                (jti,),
            )


async def revoke_token(jti: str) -> None:
    """Async wrapper — call from route handlers (e.g. logout)."""
    import asyncio
    await asyncio.to_thread(_revoke_token_sync, jti)


# ── Token decode ─────────────────────────────────────────────────────────────

def decode_session_token(token: str) -> Optional[SessionUser]:
    """Decode, verify, and revocation-check a JWT session token.

    Returns None on any failure (expired, bad signature, revoked, etc.).
    Revocation is checked synchronously against the DB — tokens in
    revoked_tokens are rejected even if they are otherwise valid.
    """
    try:
        payload = jwt.decode(token, config.SESSION_SECRET, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.debug("JWT decode failed: %s", e)
        return None

    jti = payload.get("jti")

    # Revocation check: if jti present and revoked, deny access.
    if jti:
        try:
            if _is_revoked_sync(jti):
                logger.info("Rejected revoked token jti=%s", jti)
                return None
        except Exception as e:
            # If the DB is unavailable, fail closed (deny).
            logger.error("Revocation DB check failed: %s — denying token", e)
            return None

    return SessionUser(
        id=payload["sub"],
        username=payload.get("username", ""),
        avatar=payload.get("avatar"),
        discriminator=payload.get("discriminator", "0"),
        jti=jti,
    )


# ── Token extraction — Bearer header ONLY (Module 9 / P2-04) ─────────────────

def _extract_token(request: Request) -> Optional[str]:
    """Resolve a raw JWT string from the Authorization: Bearer header.

    This is the SOLE accepted credential transport. Cookie-based extraction
    was removed in Module 9: cookies are not a safe auth transport for a
    bearer-only API because they are auto-attached by browsers, which would
    re-introduce CSRF risk. See the module docstring above.

    Returns the raw token string, or ``None`` if the header is absent /
    malformed.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith(_BEARER_PREFIX):
        return auth_header[len(_BEARER_PREFIX):]
    return None


def get_current_user(request: Request) -> Optional[SessionUser]:
    """Extract the current user from the Authorization: Bearer header.

    Returns ``None`` if the header is absent or the token is invalid /
    revoked. No cookie fallback exists — Bearer is the sole transport.
    """
    token = _extract_token(request)
    if not token:
        return None
    return decode_session_token(token)
