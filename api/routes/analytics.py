"""
Analytics API endpoints — platform-wide insights.

GET /analytics/overview  — high-level platform metrics
GET /analytics/topics    — global topic distribution
GET /analytics/activity  — daily activity trend
"""

import logging
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Query

from api.schemas.analytics import (
    ActivityAnalytics,
    DailyActivity,
    PlatformOverview,
    TopicAnalytics,
)
from api.schemas.common import APIResponse
from db import database
from utils.time_utils import today_str, parse_date
from datetime import timedelta

logger = logging.getLogger("dsa_bot.api.analytics")

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ── Platform Overview ────────────────────────────────────────────────────────

@router.get(
    "/overview",
    response_model=APIResponse[PlatformOverview],
    summary="Platform overview",
    description="Aggregate metrics across all active users: total users, messages, "
                "average consistency, and the global longest streak.",
)
async def platform_overview():
    users = await database.get_all_active_users()
    leaderboard = await database.get_leaderboard_data()

    total_users = len(users)
    active_users = sum(1 for u in leaderboard if u.get("current_streak", 0) > 0)
    total_messages = sum(u.get("total_messages", 0) for u in leaderboard)
    total_days = sum(u.get("days_posted", 0) for u in leaderboard)

    consistencies = [u.get("consistency", 0.0) for u in leaderboard]
    avg_consistency = round(sum(consistencies) / len(consistencies), 1) if consistencies else 0.0

    streaks = [u.get("current_streak", 0) for u in leaderboard]
    avg_streak = round(sum(streaks) / len(streaks), 1) if streaks else 0.0

    # Global longest streak
    longest = 0
    longest_user = None
    for u in leaderboard:
        if u.get("longest_streak", 0) > longest:
            longest = u["longest_streak"]
            longest_user = u.get("discord_username")

    return APIResponse(
        data=PlatformOverview(
            total_users=total_users,
            active_users=active_users,
            total_messages=total_messages,
            total_days_tracked=total_days,
            avg_consistency_pct=avg_consistency,
            avg_streak=avg_streak,
            longest_streak_global=longest,
            longest_streak_user=longest_user,
        )
    )


# ── Topic Analytics ──────────────────────────────────────────────────────────

@router.get(
    "/topics",
    response_model=APIResponse[TopicAnalytics],
    summary="Global topic analysis",
    description="Aggregated DSA topic distribution across all users. "
                "Shows which topics the community studies most.",
)
async def global_topics(
    limit: int = Query(20, ge=1, le=50, description="Max topics to return"),
):
    users = await database.get_all_active_users()
    all_topics: list[str] = []

    for user in users:
        logs = await database.get_progress_logs(user["user_id"])
        for log in logs:
            if log.get("topics"):
                all_topics.extend(log["topics"].split(", "))

    counter = Counter(all_topics)
    top = counter.most_common(limit)

    return APIResponse(
        data=TopicAnalytics(
            total_mentions=len(all_topics),
            unique_topics=len(counter),
            top_topics=[{"topic": t, "count": c} for t, c in top],
        )
    )


# ── Activity Trend ───────────────────────────────────────────────────────────

@router.get(
    "/activity",
    response_model=APIResponse[ActivityAnalytics],
    summary="Activity trend",
    description="Daily posting activity across all users. "
                "Use the 'period' query parameter to control the window: 7d, 30d, or all.",
)
async def activity_trend(
    period: str = Query("30d", description="Time window: '7d', '30d', or 'all'"),
):
    users = await database.get_all_active_users()
    today = today_str()

    # Determine date range
    if period == "7d":
        days = 7
    elif period == "all":
        days = 365  # reasonable cap
    else:
        days = 30

    start_date = (parse_date(today) - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    # Collect daily_status rows from all users
    day_map: dict[str, dict] = {}  # date → {"users_posted": int, "total_messages": int}

    for user in users:
        statuses = await database.get_daily_statuses_range(user["user_id"], start_date, today)
        for s in statuses:
            d = s["date"]
            if d not in day_map:
                day_map[d] = {"users_posted": 0, "total_messages": 0}
            if s.get("posted_flag"):
                day_map[d]["users_posted"] += 1

        logs = await database.get_progress_logs(user["user_id"], start_date, today)
        for log in logs:
            d = log["log_date"]
            if d not in day_map:
                day_map[d] = {"users_posted": 0, "total_messages": 0}
            day_map[d]["total_messages"] += 1

    # Build sorted daily list
    daily = sorted(
        [
            DailyActivity(date=d, users_posted=v["users_posted"], total_messages=v["total_messages"])
            for d, v in day_map.items()
        ],
        key=lambda x: x.date,
    )

    active_days = sum(1 for d in daily if d.users_posted > 0)

    return APIResponse(
        data=ActivityAnalytics(
            period=period,
            total_days=len(daily),
            active_days=active_days,
            daily_activity=daily,
        )
    )
