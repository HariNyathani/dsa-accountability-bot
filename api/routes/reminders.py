"""
Reminder API endpoints.

GET    /reminders/{user_id}  — view schedule + today's status
POST   /reminders            — update reminder times
DELETE /reminders/{user_id}  — reset to defaults

Security: all three endpoints require authentication (401 for anonymous
callers) and ownership verification (403 if the authenticated user does
not own the target user_id). Fixes P2-01 (Reminders IDOR).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import get_current_user
from api.middleware.error_handler import BadRequestError, NotFoundError
from api.schemas.common import APIResponse
from api.schemas.reminders import (
    ReminderDeleteResponse,
    ReminderSchedule,
    ReminderStatus,
    ReminderUpdateRequest,
)
from db import database
from utils.time_utils import today_str

logger = logging.getLogger("dsa_bot.api.reminders")

router = APIRouter(prefix="/reminders", tags=["Reminders"])


def _fmt(h: int, m: int) -> str:
    return f"{h:02d}:{m:02d}"


def _parse_hm(val: str) -> tuple[int, int]:
    parts = val.split(":")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError
    return h, m


async def _ensure(uid: str):
    uid_int = int(uid)
    u = await database.get_user(uid_int)
    if not u:
        raise NotFoundError("User", uid)
    return u, uid_int


def _check_owner(user_id: str, current_user) -> None:
    """Raise 401 if unauthenticated, 403 if authenticated but not the owner."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    c_id = current_user.id if hasattr(current_user, "id") else current_user.get("id")
    if str(c_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get(
    "/{user_id}",
    response_model=APIResponse[ReminderSchedule],
    summary="Get reminder schedule",
)
async def get_reminders(
    user_id: str,
    current_user=Depends(get_current_user),
):
    _check_owner(user_id, current_user)
    user, uid_int = await _ensure(user_id)
    s = await database.get_user_settings(uid_int)
    if not s:
        raise NotFoundError("Settings", user_id)

    return APIResponse(data=ReminderSchedule(
        user_id=user_id,
        timezone=user.get("timezone", "Asia/Kolkata"),
        deadline=_fmt(s["deadline_hour"], s["deadline_minute"]),
        warn_time=_fmt(s["warn_hour"], s["warn_minute"]),
        final_time=_fmt(s["final_hour"], s["final_minute"]),
        email_time=_fmt(s["email_hour"], s["email_minute"]),
        email_configured=bool(user.get("email")),
    ))


@router.post(
    "",
    response_model=APIResponse[ReminderSchedule],
    summary="Update reminder schedule",
)
async def update_reminders(
    body: ReminderUpdateRequest,
    current_user=Depends(get_current_user),
):
    # Auth check: reject anonymous callers immediately.
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Ownership: ignore any user_id the client sends in the body; always
    # operate on the authenticated caller's own ID. This eliminates the
    # body-supplied IDOR vector regardless of what body.user_id contains.
    authed_id = str(current_user.id if hasattr(current_user, "id") else current_user.get("id"))
    user, uid_int = await _ensure(authed_id)
    updates: dict = {}

    try:
        if body.warn_time:
            h, m = _parse_hm(body.warn_time)
            updates.update(warn_hour=h, warn_minute=m)
        if body.final_time:
            h, m = _parse_hm(body.final_time)
            updates.update(final_hour=h, final_minute=m)
        if body.email_time:
            h, m = _parse_hm(body.email_time)
            updates.update(email_hour=h, email_minute=m)
        if body.deadline:
            h, m = _parse_hm(body.deadline)
            updates.update(deadline_hour=h, deadline_minute=m)
    except (ValueError, IndexError):
        raise BadRequestError("Invalid time format. Use HH:MM (00:00–23:59).")

    if updates:
        await database.update_user_settings(uid_int, **updates)

    # Return updated settings
    s = await database.get_user_settings(uid_int)
    return APIResponse(data=ReminderSchedule(
        user_id=authed_id,
        timezone=user.get("timezone", "Asia/Kolkata"),
        deadline=_fmt(s["deadline_hour"], s["deadline_minute"]),
        warn_time=_fmt(s["warn_hour"], s["warn_minute"]),
        final_time=_fmt(s["final_hour"], s["final_minute"]),
        email_time=_fmt(s["email_hour"], s["email_minute"]),
        email_configured=bool(user.get("email")),
    ))


@router.delete(
    "/{user_id}",
    response_model=APIResponse[ReminderDeleteResponse],
    summary="Reset reminders to defaults",
)
async def delete_reminders(
    user_id: str,
    current_user=Depends(get_current_user),
):
    _check_owner(user_id, current_user)
    _, uid_int = await _ensure(user_id)
    await database.reset_user_settings(uid_int)
    return APIResponse(data=ReminderDeleteResponse(user_id=user_id))
