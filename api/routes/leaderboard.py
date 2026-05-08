"""
Leaderboard API endpoints.

GET /leaderboard               — default (streak-sorted) leaderboard
GET /leaderboard/streaks       — sorted by current streak
GET /leaderboard/consistency   — sorted by consistency %
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from api.schemas.common import APIResponse
from api.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse
from db import database

logger = logging.getLogger("dsa_bot.api.leaderboard")

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

# Valid sort keys matching existing leaderboard_handler.SORT_KEYS
_VALID_SORTS = {"streak", "longest", "consistency", "posts", "days"}
_SORT_KEY_MAP = {
    "streak": "current_streak",
    "longest": "longest_streak",
    "consistency": "consistency",
    "posts": "total_messages",
    "days": "days_posted",
}


async def _build_leaderboard(sort_by: str, limit: int = 25) -> LeaderboardResponse:
    """Shared leaderboard builder reusing database.get_leaderboard_data()."""
    data = await database.get_leaderboard_data()

    sort_key = _SORT_KEY_MAP.get(sort_by, "current_streak")
    data.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    total_users = len(data)
    active_streaks = sum(1 for d in data if d.get("current_streak", 0) > 0)
    entries = []

    for rank, entry in enumerate(data[:limit], start=1):
        entries.append(
            LeaderboardEntry(
                rank=rank,
                user_id=str(entry["user_id"]),
                discord_username=entry.get("discord_username"),
                current_streak=entry.get("current_streak", 0),
                longest_streak=entry.get("longest_streak", 0),
                consistency_pct=entry.get("consistency", 0.0),
                total_messages=entry.get("total_messages", 0),
                days_posted=entry.get("days_posted", 0),
            )
        )

    return LeaderboardResponse(
        sort_by=sort_by,
        total_users=total_users,
        active_streaks=active_streaks,
        entries=entries,
    )


# ── Default ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=APIResponse[LeaderboardResponse],
    summary="Get leaderboard",
    description="Returns the leaderboard sorted by the specified criterion. "
                "Valid sort values: streak, longest, consistency, posts, days.",
)
async def get_leaderboard(
    sort_by: str = Query("streak", description="Sort criterion"),
    limit: int = Query(25, ge=1, le=100, description="Max entries to return"),
):
    if sort_by not in _VALID_SORTS:
        sort_by = "streak"
    result = await _build_leaderboard(sort_by, limit)
    return APIResponse(data=result)


# ── Convenience Aliases ──────────────────────────────────────────────────────

@router.get(
    "/streaks",
    response_model=APIResponse[LeaderboardResponse],
    summary="Leaderboard by streaks",
    description="Shortcut for leaderboard sorted by current streak.",
)
async def leaderboard_streaks(
    limit: int = Query(25, ge=1, le=100),
):
    return APIResponse(data=await _build_leaderboard("streak", limit))


@router.get(
    "/consistency",
    response_model=APIResponse[LeaderboardResponse],
    summary="Leaderboard by consistency",
    description="Shortcut for leaderboard sorted by consistency percentage.",
)
async def leaderboard_consistency(
    limit: int = Query(25, ge=1, le=100),
):
    return APIResponse(data=await _build_leaderboard("consistency", limit))
