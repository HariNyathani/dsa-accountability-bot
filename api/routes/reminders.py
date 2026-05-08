"""
Reminder API endpoints.

GET    /reminders/{user_id}  — view schedule + today's status
POST   /reminders            — update reminder times
DELETE /reminders/{user_id}  — reset to defaults
"""

import logging

from fastapi import APIRouter

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


@router.get(
    "/{user_id}",
    response_model=APIResponse[ReminderSchedule],
    summary="Get reminder schedule",
)
async def get_reminders(user_id: str):
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
async def update_reminders(body: ReminderUpdateRequest):
    user, uid_int = await _ensure(body.user_id)
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
        user_id=body.user_id,
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
async def delete_reminders(user_id: str):
    _, uid_int = await _ensure(user_id)
    await database.reset_user_settings(uid_int)
    return APIResponse(data=ReminderDeleteResponse(user_id=user_id))
