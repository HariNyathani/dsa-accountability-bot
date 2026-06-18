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
from handlers.summary_handler import _extract_exposure_topics

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
    leaderboard_result = await database.get_leaderboard_data()
    total_users = leaderboard_result["total_registered_users"]
    leaderboard = leaderboard_result["rankings"]

    active_users = len(leaderboard)  # every row already has streak >= 1
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
    # Single bulk query — replaces per-user N+1 loop
    logs = await database.get_all_progress_topics()
    all_topics: list[str] = []

    for log in logs:
        all_topics.extend(_extract_exposure_topics(log))

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
    today = today_str()

    # Determine date range
    if period == "7d":
        days = 7
    elif period == "all":
        days = 365  # reasonable cap
    else:
        days = 30

    start_date = (parse_date(today) - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    # Two GROUP BY queries in a single connection checkout — replaces 2×N loop
    bulk = await database.get_activity_trend_bulk(start_date, today)

    # Merge the two result sets into a day_map
    day_map: dict[str, dict] = {}

    for row in bulk["statuses"]:
        d = row["date"]
        day_map[d] = {"users_posted": row["users_posted"], "total_messages": 0}

    for row in bulk["logs"]:
        d = row["date"]
        if d not in day_map:
            day_map[d] = {"users_posted": 0, "total_messages": 0}
        day_map[d]["total_messages"] = int(row["total_messages"] or 0)

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

