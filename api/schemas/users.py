"""
User-related Pydantic schemas.
"""

from typing import List, Optional
from pydantic import BaseModel

class EmailUpdateRequest(BaseModel):
    email: str

class TimezoneUpdateRequest(BaseModel):
    timezone: str

class UsernameUpdateRequest(BaseModel):
    user_id: str
    username: str


class UserBase(BaseModel):
    """Core user fields exposed by the API."""
    user_id: str
    discord_username: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    timezone: str = "Asia/Kolkata"
    is_active: bool = True
    created_at: Optional[str] = None


class UserSettings(BaseModel):
    """Per-user bot configuration."""
    tracked_channel_id: int = 0
    deadline_hour: int = 23
    deadline_minute: int = 0
    warn_hour: int = 22
    warn_minute: int = 0
    final_hour: int = 23
    final_minute: int = 0
    email_hour: int = 23
    email_minute: int = 30


class UserDetail(UserBase):
    """Full user profile returned by GET /users/{id}."""
    settings: Optional[UserSettings] = None


class UserStreak(BaseModel):
    """Streak data for a single user."""
    user_id: str
    current_streak: int = 0
    longest_streak: int = 0
    last_post_date: Optional[str] = None


class UserStats(BaseModel):
    """Aggregate stats for a single user."""
    user_id: str
    total_messages: int = 0
    total_days_tracked: int = 0
    days_posted: int = 0
    consistency_pct: float = 0.0
    current_streak: int = 0
    longest_streak: int = 0
    posted_today: bool = False
    today: str = ""
    badges: List[str] = []


class TopicFrequency(BaseModel):
    """A single topic and its mention count."""
    topic: str
    count: int


class UserTopics(BaseModel):
    """Topic analysis for a user."""
    user_id: str
    total_mentions: int = 0
    unique_topics: int = 0
    frequency: List[TopicFrequency] = []


class ActivityLog(BaseModel):
    """A single progress log entry for activity feed."""
    id: int
    posted_at: str
    message_type: str
    message_content: Optional[str] = None
    topics: Optional[str] = None
    parsed_fields: Optional[str] = None


class UserActivityResponse(BaseModel):
    """Recent activity for a user."""
    user_id: str
    recent_logs: List[ActivityLog]

class HeatmapResponse(BaseModel):
    user_id: str
    dates: dict[str, int]
    rest_dates: List[str] = []
    active_days: int
    current_streak: int
    max_streak: int

class UserDifficulty(BaseModel):
    user_id: str
    easy: int
    medium: int
    hard: int
    expert: int = 0
    unknown: int


class DashboardAggregateResponse(BaseModel):
    user_id: str
    stats: UserStats
    topics: UserTopics
    difficulty: UserDifficulty

