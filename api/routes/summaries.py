"""
Summary API endpoints.

GET /summaries/{user_id}      — historical weekly summaries
GET /weekly-report/{user_id}  — current / last-week live report
"""

import logging
from collections import Counter

from fastapi import APIRouter, Query

from api.middleware.error_handler import NotFoundError
from api.schemas.common import APIResponse
from api.schemas.summaries import SummaryHistory, WeeklyReport, WeeklySummary
from db import database
from utils.streak_utils import recalculate_streak
from utils.time_utils import last_week_boundaries, week_boundaries

logger = logging.getLogger("dsa_bot.api.summaries")

router = APIRouter(tags=["Summaries"])


async def _ensure_user(user_id: str) -> dict:
    uid_int = int(user_id)
    user = await database.get_user(uid_int)
    if not user:
        raise NotFoundError("User", user_id)
    return user


@router.get(
    "/summaries/{user_id}",
    response_model=APIResponse[SummaryHistory],
    summary="Weekly summary history",
)
async def get_summaries(user_id: str):
    await _ensure_user(user_id)
    uid_int = int(user_id)
    conn = await database.get_connection()
    try:
        cursor = await conn.execute(
            "SELECT week_start, week_end, days_posted, days_missed, "
            "consistency_percentage, total_messages "
            "FROM weekly_summaries WHERE user_id = ? ORDER BY week_start DESC",
            (uid_int,),
        )
        rows = await cursor.fetchall()
    finally:
        await conn.close()

    summaries = [
        WeeklySummary(
            week_start=r["week_start"], week_end=r["week_end"],
            days_posted=r["days_posted"], days_missed=r["days_missed"],
            consistency_pct=r["consistency_percentage"],
            total_messages=r["total_messages"],
        )
        for r in rows
    ]
    return APIResponse(data=SummaryHistory(user_id=user_id, summaries=summaries))


@router.get(
    "/weekly-report/{user_id}",
    response_model=APIResponse[WeeklyReport],
    summary="Live weekly report",
)
async def get_weekly_report(
    user_id: str,
    week: str = Query("last", description="'current' or 'last'"),
):
    await _ensure_user(user_id)
    uid_int = int(user_id)
    if week == "current":
        ws, we = week_boundaries()
    else:
        ws, we = last_week_boundaries()

    statuses = await database.get_daily_statuses_range(uid_int, ws, we)
    logs = await database.get_progress_logs(uid_int, ws, we)
    streak = await recalculate_streak(uid_int)

    dp = sum(1 for s in statuses if s["posted_flag"])
    cons = round((dp / 7) * 100, 1) if dp else 0.0

    all_t: list[str] = []
    for log in logs:
        if log.get("topics"):
            all_t.extend(log["topics"].split(", "))
    top = [{"topic": t, "count": c} for t, c in Counter(all_t).most_common(5)]

    return APIResponse(data=WeeklyReport(
        user_id=user_id, week_start=ws, week_end=we,
        days_posted=dp, days_missed=7 - dp, consistency_pct=cons,
        total_messages=len(logs),
        current_streak=streak["current_streak"],
        longest_streak=streak["longest_streak"],
        top_topics=top,
    ))
