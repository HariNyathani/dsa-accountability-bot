"""
Admin authentication dependency for the Admin Panel.

Validates the active session AND confirms the Discord ID matches
the ADMIN_DISCORD_ID environment variable. Raises HTTP 403 on
any failure — never 401, to prevent resource enumeration.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException

from api.middleware.auth import get_current_user, SessionUser
import config

logger = logging.getLogger("dsa_bot.api.admin_auth")


def require_admin(current_user: Optional[SessionUser] = Depends(get_current_user)) -> SessionUser:
    """
    FastAPI dependency: blocks any request where the session user
    is not the configured ADMIN_DISCORD_ID.

    Security design:
    - Always raises 403 (never 401) to avoid revealing that the
      resource exists to unauthenticated users.
    - Returns the validated SessionUser for downstream use.
    """
    if not current_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not config.ADMIN_DISCORD_ID:
        # Admin panel disabled when env var is not configured
        logger.warning("Admin access attempted but ADMIN_DISCORD_ID is not configured.")
        raise HTTPException(status_code=403, detail="Forbidden")

    if str(current_user.id) != str(config.ADMIN_DISCORD_ID):
        logger.warning(
            "Admin access denied for user %s (%s) — expected %s",
            current_user.username, current_user.id, config.ADMIN_DISCORD_ID,
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    return current_user
