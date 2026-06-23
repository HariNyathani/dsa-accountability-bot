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
    confidence: Optional[int] = Field(
        None,
        ge=1, le=5,
        description="SRS confidence score 1-5. Triggers revision_bank scheduling when provided."
    )
    is_review: Optional[bool] = Field(
        False,
        description="True if this is a spaced-repetition review session (does not update streak)."
    )

class LogProgressData(BaseModel):
    msg_type: str
    topics_logged: List[str]
    streak_current: int
    streak_longest: int

class LogProgressResponse(APIResponse[LogProgressData]):
    pass


# ── Platform Logging (LeetCode, Codeforces, CodeChef) ────────────────────────

class PlatformLogRequest(BaseModel):
    platform: str = Field(..., description="Platform name: 'leetcode', 'codeforces', or 'codechef'")
    problem_identifier: str = Field(..., description="Problem ID (number), URL, or slug")
    confidence: Optional[int] = Field(
        None,
        ge=1, le=5,
        description="SRS confidence score 1-5 (LeetCode only). Triggers revision_bank scheduling."
    )
    is_review: Optional[bool] = Field(
        False,
        description="True if this is a spaced-repetition review session (does not update streak)."
    )

class PlatformLogParsedData(BaseModel):
    title: str
    difficulty: str
    topics: List[str]
    question_id: int
    platform: str
    streak_current: int
    streak_longest: int

class PlatformLogResponse(APIResponse[PlatformLogParsedData]):
    pass


# ── Revision Bank (Spaced Repetition) ────────────────────────────────────────

class RevisionDueItem(BaseModel):
    """A single overdue revision-bank entry joined with leetcode_problems metadata."""
    problem_id: int
    title: str
    title_slug: str
    difficulty: str
    topics: List[str]
    confidence_last: int = Field(..., description="Last self-reported confidence score 1-5")
    next_review_at: str = Field(..., description="ISO-8601 UTC timestamp when this item became due")
    first_solved_at: str = Field(..., description="ISO-8601 UTC timestamp of the original solve")
    last_reviewed_at: Optional[str] = Field(None, description="ISO-8601 UTC timestamp of the last review")
    review_count: int = Field(..., description="Total number of times this problem has been reviewed")


class RevisionReviewRequest(BaseModel):
    """Payload for POST /progress/revision/review."""
    problem_id: int = Field(..., description="LeetCode question_id to mark as reviewed")
    confidence: int = Field(..., ge=1, le=5, description="Self-reported confidence score 1-5")


class RevisionReviewResponse(BaseModel):
    success: bool
    message: str
    next_review_at: str = Field(..., description="ISO-8601 UTC timestamp for the next scheduled review")
    confidence: int
    interval_days: int = Field(..., description="Number of days until the next review")


# ── Revision Bank — Full Bank Endpoint ───────────────────────────────────────

class RevisionBankItem(BaseModel):
    """Full revision-bank entry — includes items not yet due.

    Mirrors RevisionDueItem but adds ``days_remaining`` so the mobile client
    can display an accurate countdown/overdue indicator without client-side
    timezone arithmetic.
    """
    problem_id: int
    title: str
    title_slug: str
    difficulty: str
    topics: List[str]
    confidence_last: int = Field(..., description="Last self-reported confidence score 1-5")
    next_review_at: str = Field(..., description="ISO-8601 UTC timestamp of next scheduled review")
    first_solved_at: str = Field(..., description="ISO-8601 UTC timestamp of the original solve")
    last_reviewed_at: Optional[str] = Field(None, description="ISO-8601 UTC timestamp of last review")
    review_count: int = Field(..., description="Total number of reviews completed")
    days_remaining: float = Field(
        ...,
        description="Days until next review (negative = overdue, ~0 = today, positive = future)",
    )


class TopicConfidenceStat(BaseModel):
    """Per-topic SRS confidence aggregate — sorted by avg_confidence ASC.

    Derived by unnesting ``leetcode_problems.topics`` (JSONB) and computing
    the mean ``confidence_last`` across all revision-bank entries for each tag.
    Lowest ``avg_confidence`` == most authentic skill weakness.
    """
    topic: str
    avg_confidence: float = Field(..., description="Mean confidence score 1.0–5.0; lower = weaker")
    problem_count: int = Field(..., description="Number of revision-bank items carrying this topic tag")


class RevisionBankPage(BaseModel):
    """Paginated revision-bank response, bundled with topic-confidence stats.

    ``topic_stats`` is returned on every page (not just page 1) so the Flutter
    client can cache it after the first load and avoid a second round-trip.
    The list is sorted ``avg_confidence ASC`` (index 0 = weakest pattern).
    """
    items: List[RevisionBankItem]
    total_count: int = Field(..., description="Total items in the user's revision bank (pre-pagination)")
    page: int
    limit: int
    topic_stats: List[TopicConfidenceStat] = Field(
        default_factory=list,
        description="All topic confidence aggregates, sorted weakest-first.",
    )
