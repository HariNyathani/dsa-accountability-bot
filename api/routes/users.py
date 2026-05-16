"""
User API endpoints.

GET /users                   — list all active users
GET /users/{user_id}         — single user with settings
GET /users/{user_id}/stats   — aggregate stats
GET /users/{user_id}/streak  — streak data
GET /users/{user_id}/topics  — topic frequency analysis
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import FileResponse

from api.middleware.error_handler import NotFoundError
from api.middleware.auth import get_current_user
from api.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from api.schemas.users import (
    TopicFrequency,
    UserBase,
    UserDetail,
    UserSettings,
    UserStats,
    UserStreak,
    UserTopics,
    ActivityLog,
    UserActivityResponse,
    EmailUpdateRequest,
    TimezoneUpdateRequest,
    HeatmapResponse,
    UserDifficulty,
    DashboardAggregateResponse,
)
from db import database
from handlers.summary_handler import get_status_report, get_topic_summary, GLOBAL_ALIAS_MAP
import json
from collections import Counter

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


def _require_auth(current_user):
    """Any logged-in user may proceed."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _verify_owner(user_id: str, current_user):
    """Only the profile owner may proceed."""
    _require_auth(current_user)
    c_id = current_user.id if hasattr(current_user, "id") else current_user.get("id")
    if str(c_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")


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
async def get_user(user_id: str, current_user = Depends(get_current_user)):
    _require_auth(current_user)
    user = await _get_user_or_404(user_id)
    uid_int = int(user_id)

    # Only expose settings to the owner
    c_id = str(current_user.id if hasattr(current_user, "id") else current_user.get("id", ""))
    is_owner = (c_id == str(user_id))

    settings = None
    if is_owner:
        settings_row = await database.get_user_settings(uid_int)
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
            email=user.get("email") if is_owner else None,  # hide email for non-owners
            timezone=user.get("timezone", "Asia/Kolkata"),
            is_active=bool(user.get("is_active", 1)),
            created_at=user.get("created_at"),
            settings=settings,
        )
    )


# ── Single User ──────────────────────────────────────────────────────────────

@router.put(
    "/{user_id}/email",
    response_model=APIResponse[UserDetail],
    summary="Update user email",
    description="Update the email address for reminders.",
)
async def update_user_email_route(user_id: str, payload: EmailUpdateRequest, current_user = Depends(get_current_user)):
    _verify_owner(user_id, current_user)
    await _get_user_or_404(user_id)
    uid_int = int(user_id)
    await database.update_user_email(uid_int, payload.email)
    return await get_user(user_id)


@router.put(
    "/{user_id}/timezone",
    response_model=APIResponse[UserDetail],
    summary="Update user timezone",
    description="Update the timezone for the user.",
)
async def update_user_timezone_route(user_id: str, payload: TimezoneUpdateRequest, current_user = Depends(get_current_user)):
    _verify_owner(user_id, current_user)
    await _get_user_or_404(user_id)
    uid_int = int(user_id)
    import asyncio
    def _update():
        with database.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET timezone = %s WHERE user_id = %s", (payload.timezone, uid_int))
    await asyncio.to_thread(_update)
    return await get_user(user_id)


# ── Dashboard Aggregate ──────────────────────────────────────────────────────

@router.get(
    "/{user_id}/dashboard-aggregate",
    response_model=APIResponse[DashboardAggregateResponse],
    summary="Get combined dashboard data",
    description="Returns topics, difficulty, and stats in a single pass to optimize database load.",
)
async def get_dashboard_aggregate(user_id: str, current_user = Depends(get_current_user)):
    _require_auth(current_user)
    await _get_user_or_404(user_id)
    uid_int = int(user_id)

    logs = await database.get_progress_logs(uid_int)
    
    all_topics = []
    diff_counts = {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "Unknown": 0}
    
    from utils.topic_extractor import normalize_topic, STRICT_CANONICAL_TOPICS
    from handlers.summary_handler import _get_entry_difficulty, _get_entry_topics

    def _map_only(tags_list):
        return [normalize_topic(t) for t in tags_list if t.strip()]

    def _normalize_and_dedup(tags_list):
        seen = set()
        normalized = []
        for t in tags_list:
            if not t.strip(): continue
            mapped = normalize_topic(t)
            if mapped not in seen:
                seen.add(mapped)
                normalized.append(mapped)
        return normalized

    for log in logs:
        if log.get("message_type") in ("plan", "rest"):
            continue
            
        topics_added = False
        pf_raw = log.get("parsed_fields")
        if pf_raw:
            try:
                pf = json.loads(pf_raw) if isinstance(pf_raw, str) else pf_raw
                log_entries = pf.get("log", [])
                for entry in log_entries:
                    q_count = entry.get("question_count", 1)
                    
                    # Difficulty (platform-agnostic)
                    diff = _get_entry_difficulty(entry)
                    if diff:
                        diff_title = diff.strip().title()
                        if diff_title in diff_counts:
                            diff_counts[diff_title] += q_count
                        else:
                            diff_counts["Unknown"] += q_count
                    else:
                        diff_counts["Unknown"] += q_count
                        
                    # Topics (platform-agnostic)
                    entry_topics = _get_entry_topics(entry)
                    if entry_topics:
                        extracted_tags = [t.strip() for t in entry_topics.split(",") if t.strip()]
                        normalized_tags = _normalize_and_dedup(extracted_tags)
                        all_topics.extend(normalized_tags * q_count)
                        topics_added = True
            except:
                pass
                
        if not topics_added:
            topics_raw = log.get("topics", "")
            if topics_raw:
                raw_topics = [t.strip() for t in topics_raw.split(",") if t.strip()]
                all_topics.extend(_map_only(raw_topics))
                diff_counts["Unknown"] += len(raw_topics)

    # Compile topics
    canonical_set = set(STRICT_CANONICAL_TOPICS)
    filtered_topics = [t for t in all_topics if t in canonical_set]
    topic_counts = Counter(filtered_topics)
    freq = [TopicFrequency(topic=t, count=c) for t, c in topic_counts.most_common()]
    
    user_topics = UserTopics(
        user_id=user_id,
        total_mentions=len(filtered_topics),
        unique_topics=len(topic_counts),
        frequency=freq,
    )
    
    user_difficulty = UserDifficulty(
        user_id=user_id,
        easy=diff_counts["Easy"],
        medium=diff_counts["Medium"],
        hard=diff_counts["Hard"],
        expert=diff_counts["Expert"],
        unknown=diff_counts["Unknown"],
    )
    
    # Stats
    report = await get_status_report(uid_int)
    user_stats = UserStats(
        user_id=user_id,
        total_messages=report["total_messages"],
        total_days_tracked=report["total_days_tracked"],
        days_posted=report["days_posted"],
        consistency_pct=report["consistency"],
        current_streak=report["current_streak"],
        longest_streak=report["longest_streak"],
        posted_today=report["posted_today"],
        today=report["today"],
        badges=report.get("badges", []),
    )
    
    return APIResponse(
        data=DashboardAggregateResponse(
            user_id=user_id,
            stats=user_stats,
            topics=user_topics,
            difficulty=user_difficulty,
        )
    )

# ── User Stats ───────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/stats",
    response_model=APIResponse[UserStats],
    summary="Get user stats",
    description="Returns aggregate statistics: messages, consistency, streak, today's status.",
)
async def get_user_stats(user_id: str, current_user = Depends(get_current_user)):
    _require_auth(current_user)
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
            badges=report.get("badges", []),
        )
    )


# ── User Streak ──────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/streak",
    response_model=APIResponse[UserStreak],
    summary="Get user streak",
    description="Returns current and longest streak information.",
)
async def get_user_streak(user_id: str, current_user = Depends(get_current_user)):
    _require_auth(current_user)
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
async def get_user_topics(user_id: str, current_user = Depends(get_current_user)):
    _require_auth(current_user)
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


# ── User Activity ────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/activity",
    response_model=APIResponse[UserActivityResponse],
    summary="Get recent user activity",
    description="Returns the user's latest progress logs for a timeline feed.",
)
async def get_user_activity(user_id: str, limit: int = Query(10, ge=1, le=50), current_user = Depends(get_current_user)):
    _require_auth(current_user)
    await _get_user_or_404(user_id)
    uid_int = int(user_id)

    logs = await database.get_recent_progress_logs(uid_int, limit=limit)
    
    activity_logs = [
        ActivityLog(
            id=log["id"],
            posted_at=log["posted_at"],
            message_type=log["message_type"],
            message_content=log["message_content"],
            topics=log["topics"],
            parsed_fields=log["parsed_fields"],
        )
        for log in logs
    ]

    return APIResponse(
        data=UserActivityResponse(
            user_id=user_id,
            recent_logs=activity_logs,
        )
    )

@router.get(
    "/{user_id}/heatmap",
    response_model=APIResponse[HeatmapResponse],
    summary="Get user heatmap",
    description="Returns daily question counts for the past year.",
)
async def get_user_heatmap_route(user_id: str, current_user = Depends(get_current_user)):
    _require_auth(current_user)
    await _get_user_or_404(user_id)
    uid_int = int(user_id)
    data = await database.get_user_heatmap(uid_int)
    return APIResponse(
        data=HeatmapResponse(
            user_id=user_id,
            dates=data["dates"],
            active_days=data["active_days"],
            current_streak=data["current_streak"],
            max_streak=data["max_streak"]
        )
    )



@router.get(
    "/{user_id}/difficulty",
    response_model=APIResponse[UserDifficulty],
    summary="Get user difficulty stats",
    description="Returns aggregate counts of easy, medium, hard problems.",
)
async def get_user_difficulty(user_id: str, current_user = Depends(get_current_user)):
    _require_auth(current_user)
    await _get_user_or_404(user_id)
    uid_int = int(user_id)
    from handlers.summary_handler import get_difficulty_summary
    diff_data = await get_difficulty_summary(uid_int)
    
    return APIResponse(
        data=UserDifficulty(
            user_id=user_id,
            easy=diff_data["Easy"],
            medium=diff_data["Medium"],
            hard=diff_data["Hard"],
            expert=diff_data.get("Expert", 0),
            unknown=diff_data["Unknown"],
        )
    )


# ── Export Data ──────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/export",
    summary="Export user progress logs",
    description="Returns a CSV file containing all progress logs for the user.",
)
async def export_user_data(user_id: str, current_user = Depends(get_current_user)):
    _verify_owner(user_id, current_user)
    await _get_user_or_404(user_id)
    uid_int = int(user_id)
    
    from services.export_service import export_progress_csv
    filepath = await export_progress_csv(uid_int)
    
    if not os.path.exists(filepath):
        raise NotFoundError("Export file", filepath)
        
    return FileResponse(
        filepath, 
        media_type="text/csv", 
        filename=os.path.basename(filepath)
    )

