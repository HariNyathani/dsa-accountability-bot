"""
Administrative API endpoints.

All routes in this module are gated by require_admin — only the
configured ADMIN_DISCORD_ID user can access them.

GET  /admin/users           — monitoring list of all registered users
POST /admin/sudo-log        — force-insert a progress entry for any user
POST /admin/undo            — revert the latest entry for a user
POST /admin/force-summary   — trigger weekly summary generation
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.middleware.admin_auth import require_admin
from api.middleware.auth import SessionUser
from api.schemas.common import APIResponse
from db import database
from handlers.summary_handler import generate_weekly_summary_all
from handlers.leaderboard_handler import get_missed_today_report
import config

logger = logging.getLogger("dsa_bot.api.admin")

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class AdminUserRow(BaseModel):
    user_id: str
    discord_username: Optional[str] = None
    is_active: bool = True
    current_streak: int = 0
    longest_streak: int = 0
    total_questions: int = 0
    consistency_pct: float = 0.0
    posted_today: bool = False

class AdminUsersResponse(BaseModel):
    users: list[AdminUserRow]
    total: int

class SudoLogRequest(BaseModel):
    user_id: str
    topic: str = Field(..., min_length=1, description="DSA topic (e.g. 'arrays', 'dp')")
    count: int = Field(1, ge=1, le=50, description="Number of questions")
    difficulty: str = Field("Medium", description="Easy, Medium, Hard, or Expert")

class UndoRequest(BaseModel):
    user_id: str

class ForceSummaryRequest(BaseModel):
    broadcast_to_discord: bool = False

class AdminActionResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[str] = None

class MissedTodayUser(BaseModel):
    user_id: str
    discord_username: Optional[str] = None

class MissedTodayResponse(BaseModel):
    users: list[MissedTodayUser]
    total: int


# ── Admin Audit Trail ────────────────────────────────────────────────────────

def _audit_log(admin: SessionUser, action: str, detail: str = ""):
    """Log admin actions to the application log for auditability."""
    logger.info(
        "🔐 ADMIN ACTION | user=%s (ID: %s) | action=%s | detail=%s",
        admin.username, admin.id, action, detail,
    )


# ── GET /admin/users ─────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=APIResponse[AdminUsersResponse],
    summary="List all users (admin monitoring view)",
    description="Returns all registered users with streak and activity data, sorted by active streak descending.",
)
async def admin_list_users(admin: SessionUser = Depends(require_admin)):
    from utils.time_utils import today_str
    today = today_str()

    metrics = await database.get_admin_user_metrics(today)
    rows = [
        AdminUserRow(
            user_id=str(m["user_id"]),
            discord_username=m.get("discord_username"),
            is_active=bool(m.get("is_active", 1)),
            current_streak=m.get("current_streak", 0),
            longest_streak=m.get("longest_streak", 0),
            total_questions=m.get("total_questions", 0),
            consistency_pct=m.get("consistency_pct", 0.0),
            posted_today=m.get("posted_today", False),
        )
        for m in metrics
    ]

    _audit_log(admin, "GET /admin/users", f"Fetched {len(rows)} users")

    return APIResponse(
        data=AdminUsersResponse(users=rows, total=len(rows))
    )


# ── GET /admin/missed-today ──────────────────────────────────────────────────

@router.get(
    "/missed-today",
    response_model=APIResponse[MissedTodayResponse],
    summary="Users who missed posting today",
)
async def admin_missed_today(admin: SessionUser = Depends(require_admin)):
    missed = await get_missed_today_report()
    users = [
        MissedTodayUser(
            user_id=str(u["user_id"]),
            discord_username=u.get("discord_username"),
        )
        for u in (missed or [])
    ]

    _audit_log(admin, "GET /admin/missed-today", f"{len(users)} users missed")

    return APIResponse(
        data=MissedTodayResponse(users=users, total=len(users))
    )


# ── POST /admin/sudo-log ────────────────────────────────────────────────────

@router.post(
    "/sudo-log",
    response_model=APIResponse[AdminActionResponse],
    summary="Force-insert a progress entry for any user",
    description="Admin override: logs a structured qdone entry on behalf of a user.",
)
async def admin_sudo_log(
    payload: SudoLogRequest,
    admin: SessionUser = Depends(require_admin),
):
    uid = int(payload.user_id)

    # Verify target user exists
    user = await database.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {payload.user_id} not found")

    # Build qdone-style command content
    content = f"!qdone {payload.topic} {payload.count} {payload.difficulty}"

    from services.progress_service import process_progress_submission
    try:
        result = await process_progress_submission(
            user_id=uid,
            content=content,
            source="admin_panel",
            channel_id=0,
            acting_user_id=int(admin.id),
        )
    except Exception as e:
        logger.error("Admin sudo-log error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

    status = result.get("status", "unknown")
    feedback = result.get("feedback_message", "Progress logged.")

    if status == "error":
        raise HTTPException(status_code=400, detail=feedback)

    _audit_log(
        admin, "POST /admin/sudo-log",
        f"User {payload.user_id}: {payload.topic} x{payload.count} [{payload.difficulty}]"
    )

    return APIResponse(
        data=AdminActionResponse(
            status="success",
            message=feedback,
            user_id=payload.user_id,
        )
    )


# ── POST /admin/sudo-rest ───────────────────────────────────────────────────

class SudoRestRequest(BaseModel):
    user_id: str

@router.post(
    "/sudo-rest",
    response_model=APIResponse[AdminActionResponse],
    summary="Log an emergency rest day for any user",
    description=(
        "Admin override: invokes the native rest-day pipeline on behalf of a "
        "user, preserving their streak.  Subject to the same daily (1/day) and "
        "monthly (4/month) limits enforced by the core logic."
    ),
)
async def admin_sudo_rest(
    payload: SudoRestRequest,
    admin: SessionUser = Depends(require_admin),
):
    uid = int(payload.user_id)

    # Verify target user exists
    user = await database.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {payload.user_id} not found")

    # Invoke the REAL rest-day path — identical to `!sudo_log @user rest`
    # on Discord.  content="!rest" triggers _classify_message → "rest",
    # which checks has_rest_today / get_monthly_rest_count, saves a proper
    # rest log with question_count=0 and message_type="rest", and updates
    # the streak via on_post.
    from services.progress_service import process_progress_submission
    try:
        result = await process_progress_submission(
            user_id=uid,
            content="!rest",
            source="admin_panel",
            channel_id=0,
            acting_user_id=int(admin.id),
        )
    except Exception as e:
        logger.error("Admin sudo-rest error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

    status = result.get("status", "unknown")
    feedback = result.get("feedback_message", "Rest day logged.")

    if status == "error":
        raise HTTPException(status_code=400, detail=feedback)

    if status == "skipped":
        raise HTTPException(status_code=400, detail="Rest day could not be processed.")

    _audit_log(
        admin, "POST /admin/sudo-rest",
        f"Emergency rest day for user {payload.user_id}",
    )

    return APIResponse(
        data=AdminActionResponse(
            status="success",
            message=f"Emergency rest day registered via Admin Panel. {feedback}",
            user_id=payload.user_id,
        )
    )


# ── POST /admin/undo ────────────────────────────────────────────────────────

@router.post(
    "/undo",
    response_model=APIResponse[AdminActionResponse],
    summary="Revert the latest log entry for a user",
    description="Deletes the most recent progress log entry and recalculates the user's streak.",
)
async def admin_undo(
    payload: UndoRequest,
    admin: SessionUser = Depends(require_admin),
):
    uid = int(payload.user_id)

    user = await database.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {payload.user_id} not found")

    success = await database.undo_last_entry(uid)
    if not success:
        raise HTTPException(status_code=404, detail=f"No log entries found for user {payload.user_id}")

    _audit_log(admin, "POST /admin/undo", f"Reverted latest entry for user {payload.user_id}")

    return APIResponse(
        data=AdminActionResponse(
            status="success",
            message=f"Latest entry reverted for user {payload.user_id}.",
            user_id=payload.user_id,
        )
    )


# ── POST /admin/force-summary ───────────────────────────────────────────────

@router.post(
    "/force-summary",
    response_model=APIResponse[AdminActionResponse],
    summary="Trigger weekly summary generation",
    description="Computes weekly summaries for all users. Optionally broadcasts results to Discord.",
)
async def admin_force_summary(
    payload: ForceSummaryRequest,
    admin: SessionUser = Depends(require_admin),
):
    try:
        # generate_weekly_summary_all needs a bot instance for Discord posting.
        # When broadcast_to_discord is False, we pass bot=None to skip posting.
        await generate_weekly_summary_all(
            bot=None,
            send=payload.broadcast_to_discord,
        )
    except Exception as e:
        logger.error("Force summary error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {e}")

    mode = "computed + broadcast to Discord" if payload.broadcast_to_discord else "computed (no Discord broadcast)"
    _audit_log(admin, "POST /admin/force-summary", mode)

    return APIResponse(
        data=AdminActionResponse(
            status="success",
            message=f"Weekly summaries {mode}.",
        )
    )
