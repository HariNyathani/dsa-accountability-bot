"""
JWT session utilities for Discord OAuth2 authentication.

Creates and verifies stateless JWT tokens stored in HttpOnly cookies or
passed via an Authorization Bearer header (mobile clients).

Token resolution order for incoming requests:
  1. ``dsa_session`` HttpOnly cookie  — web / browser sessions.
  2. ``Authorization: Bearer <token>`` header — mobile app sessions.

The same ``decode_session_token`` validator is used for both sources so
all expiry, signature, and algorithm checks are applied uniformly.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from jose import JWTError, jwt
from fastapi import Request
from pydantic import BaseModel

import config

logger = logging.getLogger("dsa_bot.api.auth")

ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 30  # 30 days — long-lived session

_BEARER_PREFIX = "Bearer "


class SessionUser(BaseModel):
    """Decoded JWT payload representing the logged-in Discord user."""
    id: str
    username: str
    avatar: Optional[str] = None
    discriminator: str = "0"


def create_session_token(user: dict) -> str:
    """Create a JWT token from Discord user info."""
    payload = {
        "sub": str(user["id"]),
        "username": user.get("username", ""),
        "avatar": user.get("avatar"),
        "discriminator": user.get("discriminator", "0"),
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, config.SESSION_SECRET, algorithm=ALGORITHM)


def decode_session_token(token: str) -> Optional[SessionUser]:
    """Decode and validate a JWT session token. Returns None on failure."""
    try:
        payload = jwt.decode(token, config.SESSION_SECRET, algorithms=[ALGORITHM])
        return SessionUser(
            id=payload["sub"],
            username=payload.get("username", ""),
            avatar=payload.get("avatar"),
            discriminator=payload.get("discriminator", "0"),
        )
    except JWTError as e:
        logger.debug("JWT decode failed: %s", e)
        return None


def _extract_token(request: Request) -> Optional[str]:
    """Resolve a raw JWT string from the request, checking both auth sources.

    Priority:
      1. ``dsa_session`` cookie  — set by the web OAuth callback.
      2. ``Authorization`` header — injected by the mobile ``ApiClient``.

    Returns the raw token string, or ``None`` if neither source is present.
    """
    # ── 1. Cookie (web sessions) ─────────────────────────────────────────
    cookie_token = request.cookies.get("dsa_session")
    if cookie_token:
        return cookie_token

    # ── 2. Authorization Bearer header (mobile sessions) ─────────────────
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith(_BEARER_PREFIX):
        return auth_header[len(_BEARER_PREFIX):]

    return None


def get_current_user(request: Request) -> Optional[SessionUser]:
    """Extract the current user from either the session cookie or a Bearer token.

    Returns ``None`` if neither source is present or the token is invalid.
    """
    token = _extract_token(request)
    if not token:
        return None
    return decode_session_token(token)
