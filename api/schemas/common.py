"""
Common response schemas used across multiple endpoints.
"""

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

T = TypeVar("T")


# ── Standard Envelope ────────────────────────────────────────────────────────

class APIResponse(BaseModel, Generic[T]):
    """Uniform JSON envelope wrapping every API response."""
    success: bool = True
    data: T
    message: str = "OK"
    timestamp: datetime = Field(default_factory=_utcnow)


class ErrorResponse(BaseModel):
    """Returned on validation or application errors."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=_utcnow)


# ── Pagination ───────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    """Pagination metadata attached to list responses."""
    page: int = 1
    per_page: int = 20
    total_items: int = 0
    total_pages: int = 0


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list wrapper."""
    success: bool = True
    data: List[T]
    pagination: PaginationMeta
    message: str = "OK"
    timestamp: datetime = Field(default_factory=_utcnow)


# ── Health & Status ──────────────────────────────────────────────────────────

class HealthCheck(BaseModel):
    """GET /health response."""
    status: str = "healthy"
    api_version: str = "1.0.0"
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=_utcnow)


class ServiceStatus(BaseModel):
    """Individual sub-service health."""
    name: str
    status: str  # "up" | "down" | "degraded"
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class SystemStatus(BaseModel):
    """GET /status response — overall system health."""
    api: str = "running"
    bot: str = "unknown"
    database: str = "unknown"
    scheduler: str = "unknown"
    services: List[ServiceStatus] = []
    registered_users: int = 0
    uptime_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=_utcnow)
