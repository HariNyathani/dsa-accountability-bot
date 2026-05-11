from pydantic import BaseModel, Field
from typing import List, Optional
from api.schemas.common import APIResponse

class ProgressTopicLog(BaseModel):
    canonical_topic: str
    question_count: int
    difficulty: Optional[str] = None

class LogProgressRequest(BaseModel):
    intent_type: str = Field(..., description="'done' or 'plan'")
    topics: List[ProgressTopicLog]
    note: Optional[str] = Field(None, description="Optional note attached to progress")
    target_date: Optional[str] = Field(None, description="YYYY-MM-DD. Defaults to today")

class LogProgressData(BaseModel):
    msg_type: str
    topics_logged: List[str]
    streak_current: int
    streak_longest: int

class LogProgressResponse(APIResponse[LogProgressData]):
    pass
