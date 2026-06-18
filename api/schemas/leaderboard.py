"""
Leaderboard-related Pydantic schemas.
"""

from typing import List, Optional
from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    """A single row on the leaderboard."""
    rank: int
    user_id: str
    discord_username: Optional[str] = None
    username: Optional[str] = None
    current_streak: int = 0
    longest_streak: int = 0
    consistency_pct: float = 0.0
    total_messages: int = 0
    days_posted: int = 0


class LeaderboardResponse(BaseModel):
    """Full leaderboard payload."""
    sort_by: str
    total_users: int
    active_streaks: int
    entries: List[LeaderboardEntry]
