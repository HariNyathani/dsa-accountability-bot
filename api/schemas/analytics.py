"""
Analytics-related Pydantic schemas.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class PlatformOverview(BaseModel):
    """High-level platform metrics."""
    total_users: int = 0
    active_users: int = 0
    total_messages: int = 0
    total_days_tracked: int = 0
    avg_consistency_pct: float = 0.0
    avg_streak: float = 0.0
    longest_streak_global: int = 0
    longest_streak_user: Optional[str] = None


class TopicAnalytics(BaseModel):
    """Platform-wide topic distribution."""
    total_mentions: int = 0
    unique_topics: int = 0
    top_topics: List[Dict[str, object]] = []


class DailyActivity(BaseModel):
    """Activity data for a single day."""
    date: str
    users_posted: int = 0
    total_messages: int = 0


class ActivityAnalytics(BaseModel):
    """Activity heatmap / trend data."""
    period: str  # "7d" | "30d" | "all"
    total_days: int = 0
    active_days: int = 0
    daily_activity: List[DailyActivity] = []
