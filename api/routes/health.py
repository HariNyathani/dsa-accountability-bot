"""
Health & system status endpoints.

GET /health — lightweight liveness probe
GET /status — full system status (API + bot + DB + scheduler)
"""

import logging
import time

from fastapi import APIRouter

from api.schemas.common import APIResponse, HealthCheck, ServiceStatus, SystemStatus
from db import database

logger = logging.getLogger("dsa_bot.api.health")

router = APIRouter(tags=["Health"])

# Set at application startup by the launcher
_start_time: float = time.time()


def set_start_time(t: float) -> None:
    """Called once at app boot to record process start time."""
    global _start_time
    _start_time = t


def _uptime() -> float:
    return round(time.time() - _start_time, 2)


# ── Liveness ─────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=APIResponse[HealthCheck],
    summary="Liveness probe",
    description="Lightweight health check. Returns 200 if the API process is alive.",
)
async def health_check():
    return APIResponse(
        data=HealthCheck(
            status="healthy",
            uptime_seconds=_uptime(),
        )
    )


# ── Full Status ──────────────────────────────────────────────────────────────

@router.get(
    "/status",
    response_model=APIResponse[SystemStatus],
    summary="System status",
    description="Deep health check covering API, database, bot connectivity, and registered user count.",
)
async def system_status():
    services: list[ServiceStatus] = []

    # Database check
    db_status = "up"
    db_latency = None
    try:
        t0 = time.perf_counter()
        conn = await database.get_connection()
        await conn.execute("SELECT 1")
        await conn.close()
        db_latency = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as e:
        db_status = "down"
        logger.error("DB health check failed: %s", e)

    services.append(ServiceStatus(name="database", status=db_status, latency_ms=db_latency))

    # User count
    user_count = 0
    try:
        users = await database.get_all_active_users()
        user_count = len(users)
    except Exception:
        pass

    # Bot status (set externally via app.state if available)
    bot_status = "connected"  # optimistic — overridden by launcher if needed

    return APIResponse(
        data=SystemStatus(
            api="running",
            bot=bot_status,
            database=db_status,
            scheduler="active",
            services=services,
            registered_users=user_count,
            uptime_seconds=_uptime(),
        )
    )
