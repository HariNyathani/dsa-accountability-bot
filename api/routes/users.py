"""
User API endpoints.

GET /users                   — list all active users
GET /users/{user_id}         — single user with settings
GET /users/{user_id}/stats   — aggregate stats
GET /users/{user_id}/streak  — streak data
GET /users/{user_id}/topics  — topic frequency analysis
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from api.middleware.error_handler import NotFoundError
from api.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from api.schemas.users import (
    TopicFrequency,
    UserBase,
    UserDetail,
    UserSettings,
    UserStats,
    UserStreak,
    UserTopics,
)
from db import database
from handlers.summary_handler import get_status_report, get_topic_summary

logger = logging.getLogger("dsa_bot.api.users")

router = APIRouter(prefix="/users", tags=["Users"])


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_user_or_404(user_id: str) -> dict:
    """Fetch user from DB or raise 404."""
    uid_int = int(user_id)
    user = await database.get_user(uid_int)
    if not user:
        raise NotFoundError("User", user_id)
    return user


# ── List Users ───────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedResponse[UserBase],
    summary="List all active users",
    description="Returns paginated list of registered active users.",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    users = await database.get_all_active_users()
    total = len(users)

    # Paginate in-memory (SQLite doesn't have efficient OFFSET for small datasets)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = users[start:end]

    total_pages = (total + per_page - 1) // per_page if total > 0 else 0

    return PaginatedResponse(
        data=[
            UserBase(
                user_id=str(u["user_id"]),
                discord_username=u.get("discord_username"),
                email=u.get("email"),
                timezone=u.get("timezone", "Asia/Kolkata"),
                is_active=bool(u.get("is_active", 1)),
                created_at=u.get("created_at"),
            )
            for u in page_items
        ],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total_items=total,
            total_pages=total_pages,
        ),
    )


# ── Single User ──────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}",
    response_model=APIResponse[UserDetail],
    summary="Get user details",
    description="Returns full user profile including bot settings.",
)
async def get_user(user_id: str):
    user = await _get_user_or_404(user_id)
    uid_int = int(user_id)
    settings_row = await database.get_user_settings(uid_int)

    settings = None
    if settings_row:
        settings = UserSettings(**{
            k: settings_row[k]
            for k in UserSettings.model_fields
            if k in settings_row
        })

    return APIResponse(
        data=UserDetail(
            user_id=str(user["user_id"]),
            discord_username=user.get("discord_username"),
            email=user.get("email"),
            timezone=user.get("timezone", "Asia/Kolkata"),
            is_active=bool(user.get("is_active", 1)),
            created_at=user.get("created_at"),
            settings=settings,
        )
    )


# ── User Stats ───────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/stats",
    response_model=APIResponse[UserStats],
    summary="Get user stats",
    description="Returns aggregate statistics: messages, consistency, streak, today's status.",
)
async def get_user_stats(user_id: str):
    await _get_user_or_404(user_id)
    uid_int = int(user_id)

    # Reuse existing handler logic — returns a rich dict
    report = await get_status_report(uid_int)

    return APIResponse(
        data=UserStats(
            user_id=user_id,
            total_messages=report["total_messages"],
            total_days_tracked=report["total_days_tracked"],
            days_posted=report["days_posted"],
            consistency_pct=report["consistency"],
            current_streak=report["current_streak"],
            longest_streak=report["longest_streak"],
            posted_today=report["posted_today"],
            today=report["today"],
        )
    )


# ── User Streak ──────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/streak",
    response_model=APIResponse[UserStreak],
    summary="Get user streak",
    description="Returns current and longest streak information.",
)
async def get_user_streak(user_id: str):
    await _get_user_or_404(user_id)
    uid_int = int(user_id)
    streak = await database.get_streak(uid_int)

    return APIResponse(
        data=UserStreak(
            user_id=user_id,
            current_streak=streak["current_streak"],
            longest_streak=streak["longest_streak"],
            last_post_date=streak.get("last_post_date"),
        )
    )


# ── User Topics ──────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/topics",
    response_model=APIResponse[UserTopics],
    summary="Get user topic analysis",
    description="Returns DSA topic frequency analysis for the user's progress logs.",
)
async def get_user_topics(user_id: str):
    await _get_user_or_404(user_id)
    uid_int = int(user_id)

    # Reuse existing handler logic
    topic_data = await get_topic_summary(uid_int)

    return APIResponse(
        data=UserTopics(
            user_id=user_id,
            total_mentions=topic_data["total_topics_mentioned"],
            unique_topics=topic_data["unique_topics"],
            frequency=[
                TopicFrequency(topic=t, count=c)
                for t, c in topic_data["frequency"]
            ],
        )
    )
