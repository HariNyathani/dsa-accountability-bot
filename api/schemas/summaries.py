"""
Summary-related Pydantic schemas.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class WeeklySummary(BaseModel):
    """A single weekly summary record."""
    week_start: str
    week_end: str
    days_posted: int = 0
    days_missed: int = 0
    consistency_pct: float = 0.0
    total_messages: int = 0


class WeeklyReport(BaseModel):
    """Rich weekly report for a user (current or last week)."""
    user_id: str
    week_start: str
    week_end: str
    days_posted: int = 0
    days_missed: int = 0
    consistency_pct: float = 0.0
    total_messages: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    top_topics: List[Dict[str, object]] = []


class SummaryHistory(BaseModel):
    """List of weekly summaries for a user."""
    user_id: str
    summaries: List[WeeklySummary] = []
