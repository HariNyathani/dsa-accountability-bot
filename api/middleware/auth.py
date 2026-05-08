"""
JWT session utilities for Discord OAuth2 authentication.

Creates and verifies stateless JWT tokens stored in HttpOnly cookies.
Tokens contain the Discord user's id, username, and avatar hash.
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


def get_current_user(request: Request) -> Optional[SessionUser]:
    """Extract the current user from the session cookie. Returns None if unauthenticated."""
    token = request.cookies.get("dsa_session")
    if not token:
        return None
    return decode_session_token(token)
