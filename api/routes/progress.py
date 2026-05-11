import logging
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import Optional

from api.schemas.progress import LogProgressRequest, LogProgressResponse, LogProgressData
from api.middleware.auth import get_current_user
from services.progress_service import process_progress_submission

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
    except Exception as e:
        logger.error(f"Error logging progress from web: {e}")
        raise HTTPException(status_code=500, detail="Failed to log progress")
