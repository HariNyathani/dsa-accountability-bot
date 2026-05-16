import logging
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import Optional

from api.schemas.progress import (
    LogProgressRequest, LogProgressResponse, LogProgressData,
    PlatformLogRequest, PlatformLogResponse, PlatformLogParsedData,
)
from api.middleware.auth import get_current_user
from services.progress_service import process_progress_submission
from utils.resolvers import resolve_problem, RESOLVERS

logger = logging.getLogger("dsa_bot.api.progress")

router = APIRouter(prefix="/progress", tags=["Progress Logging"])

def require_auth(request: Request) -> int:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return int(user.id)

@router.post("/", response_model=LogProgressResponse)
async def log_progress(
    request: LogProgressRequest,
    user_id: int = Depends(require_auth)
):
    """
    Log DSA progress or plans from the web dashboard.
    Records data into the same history stream as Discord commands.
    """
    try:
        # Reconstruct a quasi-Discord message format so our backend
        # logic handles it naturally without code branching.
        content_lines = []
        if request.intent_type == "done":
            cmd = "!qdone " + " ".join([f"{t.canonical_topic} {t.question_count}" for t in request.topics])
            content_lines.append(cmd)
        elif request.intent_type == "plan":
            cmd = "!plan tomorrow " + ", ".join([t.canonical_topic for t in request.topics])
            content_lines.append(cmd)
        else:
            raise HTTPException(status_code=400, detail="Invalid intent_type")
            
        if request.note:
            content_lines.append(request.note)
            
        final_content = "\n".join(content_lines)
        
        web_topics = []
        if request.intent_type == "done":
            web_topics = [{"canonical_topic": t.canonical_topic, "question_count": t.question_count, "difficulty": t.difficulty} for t in request.topics]

        result = await process_progress_submission(
            user_id=user_id,
            content=final_content,
            source="web",
            override_date=request.target_date,
            web_topics=web_topics if web_topics else None
        )
        
        if result.get("status") == "skipped":
            return LogProgressResponse(
                success=True,
                message="Duplicate log skipped.",
                data=LogProgressData(
                    msg_type="skipped",
                    topics_logged=[],
                    streak_current=0,
                    streak_longest=0
                )
            )
            
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("feedback_message", "Invalid submission"))
            
        streak = result.get("streak", {})
        feedback = result.get("feedback_message", "Progress logged successfully")
        
        return LogProgressResponse(
            success=True,
            message=feedback,
            data=LogProgressData(
                msg_type=result["msg_type"],
                topics_logged=result["topics"],
                streak_current=streak.get("current_streak", 0),
                streak_longest=streak.get("longest_streak", 0)
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging progress from web: {e}")
        raise HTTPException(status_code=500, detail="Failed to log progress")

@router.post(
    "/rest",
    response_model=LogProgressResponse,
    summary="Log a rest day",
    description="Registers a rest day for the user, subject to monthly and daily limits.",
)
async def log_rest_day(user_id: int = Depends(require_auth)):
    try:
        result = await process_progress_submission(
            user_id=user_id,
            content="!rest",
            source="web"
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("feedback_message", "Failed to log rest day"))
            
        streak = result.get("streak", {})
        feedback = result.get("feedback_message", "Rest Day Logged. See you tomorrow, legend!")
        
        return LogProgressResponse(
            success=True,
            message=feedback,
            data=LogProgressData(
                msg_type=result.get("msg_type", "rest"),
                topics_logged=[],
                streak_current=streak.get("current_streak", 0),
                streak_longest=streak.get("longest_streak", 0)
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging rest day from web: {e}")
        raise HTTPException(status_code=500, detail="Failed to log rest day")


@router.post(
    "/platform",
    response_model=PlatformLogResponse,
    summary="Log a problem from a competitive programming platform",
    description="Resolve a problem by ID/URL on a supported platform (LeetCode, Codeforces), then log it as progress.",
)
async def log_platform_problem(
    request: PlatformLogRequest,
    user_id: int = Depends(require_auth),
):
    """
    Platform-aware problem logging.
    Uses the Strategy-pattern resolver registry to dispatch to the correct
    platform resolver (LeetCode, Codeforces).
    """
    platform = request.platform.lower().strip()
    identifier = request.problem_identifier.strip()

    # ── Gate: Only registered platforms are supported ──────────────────
    if platform not in RESOLVERS:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' is not supported. Available: {', '.join(RESOLVERS.keys())}.",
        )

    if not identifier:
        raise HTTPException(status_code=400, detail="Problem identifier cannot be empty.")

    try:
        # ── Step 1: Resolve problem via platform-specific resolver ────
        match = await resolve_problem(identifier, platform=platform)

        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find a {platform.title()} problem matching '{identifier}'. Try a valid problem ID, URL, or title.",
            )

        # ── Step 2: Attempt the standard pipeline first (works for LC) ─
        content = f"!log {identifier}"

        result = await process_progress_submission(
            user_id=user_id,
            content=content,
            source="web",
        )

        # ── Step 3: Direct insertion for non-LC platforms ─────────────
        # The NLP pipeline in progress_service is LeetCode-aware only.
        # For Codeforces, we bypass it and insert directly using the
        # resolved data from the Strategy-pattern resolver.
        if result.get("status") in ("skipped", "error") and platform != "leetcode":
            from db import database
            from utils.time_utils import today_str, now_iso
            from utils.streak_utils import on_post
            import json

            user = await database.get_user(user_id)
            user_tz = user.get("timezone", "") if user else ""
            today = today_str(user_tz)
            now = now_iso(user_tz)

            parsed_fields_dict = {
                "intent_type": "done",
                "target_date": today,
                "source": "web",
                "platform": platform,
                "log": [{
                    "canonical_topic": match.title,
                    "normalized_topic": match.title,
                    "question_count": 1,
                    # Unified keys — used by analytics aggregation
                    "difficulty": match.difficulty_norm,
                    "topics": match.topics_str,
                    # Platform-specific keys — kept for provenance/debugging
                    f"{platform}_title": match.title,
                    f"{platform}_topics": match.topics_str,
                    f"{platform}_difficulty": match.difficulty_norm,
                    f"{platform}_difficulty_raw": match.difficulty_raw,
                }],
            }

            # Preserve raw CF rating in parsed_fields
            if match.extra.get("cf_rating") is not None:
                parsed_fields_dict["log"][0]["cf_rating"] = match.extra["cf_rating"]

            # Rate limit check
            current_sum = await database.get_daily_question_count(user_id, today)
            if (current_sum + 1) > 200:
                raise HTTPException(
                    status_code=400,
                    detail="Daily limit reached (200/day). Quality over quantity, legend! See you tomorrow.",
                )

            await database.save_progress_log(
                user_id=user_id,
                channel_id=0,
                message_content=content,
                topics=match.title,
                posted_at=now,
                log_date=today,
                message_type="done",
                parsed_fields=json.dumps(parsed_fields_dict),
                platform=platform,
            )

            await database.mark_posted(user_id, today)
            streak = await on_post(user_id, today)

            result = {
                "status": "success",
                "feedback_message": (
                    f"✅ Logged 1 question: {match.title} [{match.difficulty_norm}]"
                    + (f" (Auto-tagged: {match.topics_str})" if match.topics_str else "")
                ),
                "streak": streak,
            }

        elif result.get("status") == "error":
            raise HTTPException(
                status_code=400,
                detail=result.get("feedback_message", "Failed to log platform problem."),
            )
        elif result.get("status") == "skipped":
            raise HTTPException(
                status_code=400,
                detail="This problem could not be matched or was skipped.",
            )

        streak = result.get("streak", {})

        return PlatformLogResponse(
            success=True,
            message=result.get("feedback_message", "Problem logged successfully."),
            data=PlatformLogParsedData(
                title=match.title,
                difficulty=match.difficulty_norm,
                topics=match.topics,
                question_id=int(match.problem_id) if match.problem_id.isdigit() else 0,
                platform=platform,
                streak_current=streak.get("current_streak", 0),
                streak_longest=streak.get("longest_streak", 0),
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in platform log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to log platform problem.")
