"""
Reminder-related Pydantic schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ReminderSchedule(BaseModel):
    """Current reminder configuration for a user."""
    user_id: str
    timezone: str = "Asia/Kolkata"
    deadline: str = "23:00"
    warn_time: str = "22:00"
    final_time: str = "23:00"
    email_time: str = "23:30"
    email_configured: bool = False


class ReminderStatus(BaseModel):
    """Today's reminder dispatch status for a user."""
    user_id: str
    date: str
    posted_today: bool = False
    warn_sent: bool = False
    final_sent: bool = False
    email_sent: bool = False


class ReminderUpdateRequest(BaseModel):
    """POST /reminders — update reminder schedule for a user."""
    user_id: str
    warn_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", examples=["22:00"])
    final_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", examples=["23:00"])
    email_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", examples=["23:30"])
    deadline: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", examples=["23:00"])


class ReminderDeleteResponse(BaseModel):
    """DELETE /reminders/{user_id} — reset confirmation."""
    user_id: str
    reset: bool = True
    message: str = "Reminder schedule reset to defaults."
