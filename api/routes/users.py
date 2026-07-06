"""
User API endpoints.

GET /users                          — list all active users
GET /users/check-username/{name}    — check vanity handle availability
PUT /users/settings/username        — claim or update vanity handle
GET /users/{identifier}             — single user (by numeric ID or username)
GET /users/{identifier}/stats       — aggregate stats
GET /users/{identifier}/streak      — streak data
GET /users/{identifier}/topics      — topic frequency analysis
"""

import logging
import os
import re
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import FileResponse

import config
from api.middleware.cache import cached_route
from api.middleware.cache_headers import public_cache
from api.middleware.error_handler import NotFoundError
from api.middleware.auth import get_current_user
from api.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from api.schemas.users import (
    TopicFrequency,
    UserBase,
    UserDetail,
    UserSettings,
    UserStats,
    UserStreak,
    UserTopics,
    ActivityLog,
    UserActivityResponse,
    EmailUpdateRequest,
    TimezoneUpdateRequest,
    UsernameUpdateRequest,
    HeatmapResponse,
    UserDifficulty,
    DashboardAggregateResponse,
)
from db import database
from handlers.summary_handler import get_status_report, get_topic_summary, GLOBAL_ALIAS_MAP
import json
from collections import Counter

logger = logging.getLogger("dsa_bot.api.users")

router = APIRouter(prefix="/users", tags=["Users"])


# ── Username blocklist & validation ──────────────────────────────────────────

RESERVED_NAMES = frozenset({
    # Legal, Operations & Support
    'contact', 'about', 'privacy', 'terms', 'tos', 'legal', 'security', 'abuse', 'noc', 'info',
    'support', 'billing', 'invoice', 'sales', 'marketing', 'jobs', 'careers', 'press', 'media',
    'helpdesk', 'status', 'compliance', 'copyright', 'disclaimer', 'service', 'services',

    # System Administration & Infrastructure
    'root', 'admin', 'administrator', 'sysadmin', 'mod', 'moderator', 'staff', 'helper', 'vip',
    'official', 'bot', 'dsabot', 'system', 'dev', 'developer', 'owner', 'founder', 'creator',
    'server', 'database', 'db', 'postgres', 'sql', 'query', 'internal', 'localhost', 'bin',
    'etc', 'var', 'ssl', 'cert', 'certificate', 'superuser', 'su', 'manager', 'webmaster',
    'webadmin', 'hostmaster', 'hostname', 'operator',

    # Common Attack/Scanner & CMS Targets
    'wordpress', 'wp', 'wpuser', 'wpadmin', 'qwerty', 'asdf', 'password', 'testuser',

    # Authentication & Identity
    'login', 'logout', 'register', 'signup', 'signin', 'signout', 'auth', 'oauth', 'session',
    'sessions', 'token', 'cookie', 'cookies', 'csrf', 'xss', 'reset-password', 'forgot-password',
    'email', 'verify', 'activate', 'invite', 'mfa', '2fa', 'captcha',

    # Web App Infrastructure & Routes
    'api', 'v1', 'v2', 'v3', 'v4', 'latest', 'graphql', 'rest', 'rpc', 'ws', 'websocket',
    'webhooks', 'webhook', 'callback', 'redirect', 'assets', 'static', 'public', 'private',
    'index', 'main', 'home', 'config', 'settings', 'preferences', 'profile', 'upload',
    'download', 'export', 'import', 'docs', 'documentation', 'changelog',

    # DSA Features & Terminology
    'problems', 'problem', 'solutions', 'solution', 'challenges', 'challenge', 'practice', 'practise',
    'exercise', 'exercises', 'tests', 'test', 'testing', 'preparation', 'prep', 'interview', 'interviews',
    'contest', 'contests', 'mock', 'arrays', 'strings', 'trees', 'graphs', 'linkedlist', 'algorithms',
    'streak', 'streaks', 'rank', 'ranking', 'rankings', 'points', 'leaderboard', 'analytics', 'dashboard', 'metrics',

    # Placeholder & Structural Code Hazards
    'me', 'null', 'undefined', 'true', 'false', 'void', 'anonymous', 'guest', 'none', 'nil',
    'default', 'user', 'user1', 'admin1', 'admin2', 'test1', 'demo', 'member', 'members',
    'community', 'everyone', 'here', 'all',

    # Static Assets, Well-Known Files & System State
    'robots.txt', 'favicon.ico', 'humans.txt', 'keybase.txt', 'sitemap', 'sitemaps', 'crossdomain.xml',
    'error', 'errors', 'exception', 'blocked', 'forbidden', 'expired', 'trial', 'account', 'accounts',
    'backup', 'backups', 'archive', 'forum', 'forums', 'wiki', 'webmail', 'newsletter', 'newsletters',
    'subscribe', 'unsubscribe',
})

_USERNAME_RE = re.compile(r'^[a-z0-9_]+$')

def _validate_username(username: str) -> tuple[bool, str]:
    """Validate format + blocklist. Returns (ok, reason)."""
    if not username or len(username) < 4:
        return False, "Username must be at least 4 characters."
    if len(username) > 20:
        return False, "Username must be at most 20 characters."
    if not _USERNAME_RE.match(username):
        return False, "Only lowercase letters, numbers, and underscores allowed."
    if username in RESERVED_NAMES:
        return False, "This username is reserved for system use."
    return True, ""


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_user_or_404(identifier: str, current_user=None) -> dict:
    """Smart resolver: numeric Discord ID → get_user, else → get_user_by_username.

    When the identifier is a numeric Discord ID and the caller is the
    authenticated owner, transparently provisions the user in the DB if the
    row is missing (lazy self-heal). This catches the case where a user
    completed OAuth login but their `users` row was never written —
    e.g. they signed in on the mobile app before any DB write path fired.
    """
    if re.fullmatch(r'\d{17,21}', identifier):
        uid = int(identifier)
        user = await database.get_user(uid)
        if not user and current_user is not None and str(current_user.id) == identifier:
            try:
                await database.register_user(
                    uid,
                    current_user.username or "",
                    timezone=config.DEFAULT_TIMEZONE,
                )
                logger.info("Lazy self-heal: registered user %s on first /users/{id} hit", uid)
                user = await database.get_user(uid)
            except Exception as e:
                logger.warning("Lazy self-heal register_user failed for %s: %s", uid, e)
    else:
        user = await database.get_user_by_username(identifier)
    if not user:
        raise NotFoundError("User", identifier)
    return user


def _require_auth(current_user):
    """Any logged-in user may proceed."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _verify_owner(user_id: str, current_user):
    """Only the profile owner may proceed."""
    _require_auth(current_user)
    c_id = current_user.id if hasattr(current_user, "id") else current_user.get("id")
    if str(c_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")


# ── List Users ───────────────────────────────────────────────────────────────

@cached_route(60)
@router.get(
    "",
    response_model=PaginatedResponse[UserBase],
    summary="List all active users",
    description="Returns paginated list of registered active users.",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    _cache: None = Depends(public_cache),
):
    users = await database.get_all_active_users()
    total = len(users)

    # Paginate in-memory (SQLite doesn't have efficient OFFSET for small datasets)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = users[start:end]

    total_pages = (total + per_page - 1) // per_page if total > 0 else 0

    return PaginatedResponse(
        data=[
            UserBase(
                user_id=str(u["user_id"]),
                discord_username=u.get("discord_username"),
                username=u.get("username"),
                email=u.get("email"),
                timezone=u.get("timezone", "Asia/Kolkata"),
                is_active=bool(u.get("is_active", 1)),
                created_at=u.get("created_at"),
            )
            for u in page_items
        ],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total_items=total,
            total_pages=total_pages,
        ),
    )


# ── Username availability & claim ────────────────────────────────────────────
# These MUST be defined before the /{identifier} catch-all so FastAPI matches
# the static path segments first.

@router.get(
    "/check-username/{username}",
    response_model=APIResponse,
    summary="Check username availability",
    description="Validates format, checks blocklist, and queries uniqueness. Public endpoint.",
)
async def check_username_route(username: str):
    clean_username = username.strip().lower()

    if clean_username in RESERVED_NAMES:
        return APIResponse(data={"available": False, "reason": "This username is reserved for system use."})

    valid, reason = _validate_username(clean_username)
    if not valid:
        return APIResponse(data={"available": False, "reason": reason})

    available = await database.check_username_available(clean_username)
    if not available:
        return APIResponse(data={"available": False, "reason": "This username is already taken."})

    return APIResponse(data={"available": True, "reason": ""})


@router.put(
    "/settings/username",
    response_model=APIResponse[UserDetail],
    summary="Claim or update vanity username",
    description="Authenticated owner-only. Validates format, checks blocklist + uniqueness, then persists.",
)
async def update_username_route(payload: UsernameUpdateRequest, current_user = Depends(get_current_user)):
    clean_username = payload.username.strip().lower()

    if clean_username in RESERVED_NAMES:
        raise HTTPException(status_code=400, detail="This username is reserved for system use.")

    _verify_owner(payload.user_id, current_user)
    await _get_user_or_404(payload.user_id, current_user)

    valid, reason = _validate_username(clean_username)
    if not valid:
        raise HTTPException(status_code=400, detail=reason)

    available = await database.check_username_available(clean_username)
    if not available:
        # Allow if the user already owns this exact username
        existing_user = await database.get_user_by_username(clean_username)
        if not existing_user or str(existing_user["user_id"]) != str(payload.user_id):
            raise HTTPException(status_code=409, detail="This username is already taken.")

    await database.set_username(int(payload.user_id), clean_username)
    # Return the updated profile (uncached helper, never read from the route cache)
    return await _get_user_response(payload.user_id, current_user)


# ── Single User ──────────────────────────────────────────────────────────────

@cached_route(60)
@router.get(
    "/{identifier}",
    response_model=APIResponse[UserDetail],
    summary="Get user details",
    description="Returns full user profile. Accepts numeric Discord ID or vanity username. Public access; personal fields redacted for non-owners.",
)
async def get_user(identifier: str, current_user = Depends(get_current_user), _cache: None = Depends(public_cache)):
    return await _get_user_response(identifier, current_user)


async def _get_user_response(identifier: str, current_user):
    """Uncached implementation of get_user — call this from mutation handlers
    so they always return the freshly-saved profile rather than a stale cached copy."""
    # Public route — no hard auth required. current_user is None for guests.
    user = await _get_user_or_404(identifier, current_user)
    user_id_str = str(user["user_id"])
    uid_int = user["user_id"]

    # Determine ownership: only the authenticated profile owner gets private fields
    c_id = ""
    if current_user:
        c_id = str(current_user.id if hasattr(current_user, "id") else current_user.get("id", ""))
    is_owner = bool(c_id) and (c_id == user_id_str)

    settings = None
    if is_owner:
        settings_row = await database.get_user_settings(uid_int)
        if settings_row:
            settings = UserSettings(**{
                k: settings_row[k]
                for k in UserSettings.model_fields
                if k in settings_row
            })

    return APIResponse(
        data=UserDetail(
            user_id=user_id_str,
            discord_username=user.get("discord_username"),
            username=user.get("username"),
            email=user.get("email") if is_owner else None,  # Redact email for public/guest viewers
            timezone=user.get("timezone", "Asia/Kolkata"),
            is_active=bool(user.get("is_active", 1)),
            created_at=user.get("created_at"),
            settings=settings,
        )
    )


# ── Email & Timezone ─────────────────────────────────────────────────────────

@router.put(
    "/{user_id}/email",
    response_model=APIResponse[UserDetail],
    summary="Update user email",
    description="Update the email address for reminders.",
)
async def update_user_email_route(user_id: str, payload: EmailUpdateRequest, current_user = Depends(get_current_user)):
    _verify_owner(user_id, current_user)
    resolved = await _get_user_or_404(user_id, current_user)
    uid_int = resolved["user_id"]
    await database.update_user_email(uid_int, payload.email)
    return await _get_user_response(user_id, current_user)


@router.put(
    "/{user_id}/timezone",
    response_model=APIResponse[UserDetail],
    summary="Update user timezone",
    description="Update the timezone for the user.",
)
async def update_user_timezone_route(user_id: str, payload: TimezoneUpdateRequest, current_user = Depends(get_current_user)):
    _verify_owner(user_id, current_user)
    resolved = await _get_user_or_404(user_id, current_user)
    uid_int = resolved["user_id"]

    # P3-05: Enforce minimum interval between timezone changes.
    # Rapid TZ-flipping can be abused to bank streaks by manipulating what
    # "today" means. A cooldown of TZ_CHANGE_COOLDOWN_MINUTES (default 60)
    # makes this attack impractical without blocking legitimate use.
    import asyncio
    import os
    from datetime import datetime, timezone as _tz

    COOLDOWN_MINUTES = int(os.getenv("TZ_CHANGE_COOLDOWN_MINUTES", "60"))

    def _get_and_update():
        with database.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Read current timezone_updated_at
                cur.execute(
                    "SELECT timezone_updated_at FROM users WHERE user_id = %s",
                    (uid_int,),
                )
                row = cur.fetchone()
                last_updated = row[0] if row else None

                if last_updated is not None:
                    now_utc = datetime.now(_tz.utc)
                    # last_updated may be timezone-aware or naive depending on
                    # psycopg2 config; normalise to UTC for comparison.
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=_tz.utc)
                    elapsed_minutes = (now_utc - last_updated).total_seconds() / 60
                    if elapsed_minutes < COOLDOWN_MINUTES:
                        remaining = int(COOLDOWN_MINUTES - elapsed_minutes) + 1
                        return ("cooldown", remaining)

                # All checks passed — update both fields atomically
                cur.execute(
                    "UPDATE users SET timezone = %s, timezone_updated_at = NOW() WHERE user_id = %s",
                    (payload.timezone, uid_int),
                )
                return ("ok", None)

    check, remaining = await asyncio.to_thread(_get_and_update)
    if check == "cooldown":
        raise HTTPException(
            status_code=429,
            detail=(
                f"Timezone changed too recently. "
                f"Please wait {remaining} more minute(s) before changing again."
            ),
        )

    return await _get_user_response(user_id, current_user)


# ── Dashboard Aggregate ──────────────────────────────────────────────────────

@cached_route(60)
@router.get(
    "/{user_id}/dashboard-aggregate",
    response_model=APIResponse[DashboardAggregateResponse],
    summary="Get combined dashboard data",
    description="Returns topics, difficulty, and stats in a single pass. Publicly accessible without authentication.",
)
async def get_dashboard_aggregate(user_id: str, _cache: None = Depends(public_cache)):
    # Public route — no auth required
    resolved = await _get_user_or_404(user_id)
    uid_int = resolved["user_id"]

    logs = await database.get_progress_logs(uid_int)
    
    all_topics = []
    diff_counts = {"Easy": 0, "Medium": 0, "Hard": 0, "Expert": 0, "Unknown": 0}
    
    from utils.topic_extractor import normalize_topic, STRICT_CANONICAL_TOPICS
    from handlers.summary_handler import _get_entry_difficulty, _get_entry_topics

    def _map_only(tags_list):
        return [normalize_topic(t) for t in tags_list if t.strip()]

    def _normalize_and_dedup(tags_list):
        seen = set()
        normalized = []
        for t in tags_list:
            if not t.strip(): continue
            mapped = normalize_topic(t)
            if mapped not in seen:
                seen.add(mapped)
                normalized.append(mapped)
        return normalized

    for log in logs:
        if log.get("message_type") in ("plan", "rest"):
            continue
            
        topics_added = False
        pf_raw = log.get("parsed_fields")
        if pf_raw:
            try:
                pf = json.loads(pf_raw) if isinstance(pf_raw, str) else pf_raw
                log_entries = pf.get("log", [])
                for entry in log_entries:
                    q_count = entry.get("question_count", 1)
                    
                    # Difficulty (platform-agnostic)
                    diff = _get_entry_difficulty(entry)
                    if diff:
                        diff_title = diff.strip().title()
                        if diff_title in diff_counts:
                            diff_counts[diff_title] += q_count
                        else:
                            diff_counts["Unknown"] += q_count
                    else:
                        diff_counts["Unknown"] += q_count
                        
                    # Topics (platform-agnostic)
                    entry_topics = _get_entry_topics(entry)
                    if entry_topics:
                        extracted_tags = [t.strip() for t in entry_topics.split(",") if t.strip()]
                        normalized_tags = _normalize_and_dedup(extracted_tags)
                        all_topics.extend(normalized_tags * q_count)
                        topics_added = True
            except:
                pass
                
        if not topics_added:
            topics_raw = log.get("topics", "")
            if topics_raw:
                raw_topics = [t.strip() for t in topics_raw.split(",") if t.strip()]
                all_topics.extend(_map_only(raw_topics))
                diff_counts["Unknown"] += len(raw_topics)

    # Compile topics
    canonical_set = set(STRICT_CANONICAL_TOPICS)
    filtered_topics = [t for t in all_topics if t in canonical_set]
    topic_counts = Counter(filtered_topics)
    freq = [TopicFrequency(topic=t, count=c) for t, c in topic_counts.most_common()]
    
    user_topics = UserTopics(
        user_id=user_id,
        total_mentions=len(filtered_topics),
        unique_topics=len(topic_counts),
        frequency=freq,
    )
    
    user_difficulty = UserDifficulty(
        user_id=user_id,
        easy=diff_counts["Easy"],
        medium=diff_counts["Medium"],
        hard=diff_counts["Hard"],
        expert=diff_counts["Expert"],
        unknown=diff_counts["Unknown"],
    )
    
    # Stats
    report = await get_status_report(uid_int)
    user_stats = UserStats(
        user_id=user_id,
        total_messages=report["total_messages"],
        total_days_tracked=report["total_days_tracked"],
        days_posted=report["days_posted"],
        consistency_pct=report["consistency"],
        current_streak=report["current_streak"],
        longest_streak=report["longest_streak"],
        posted_today=report["posted_today"],
        today=report["today"],
        badges=report.get("badges", []),
    )
    
    return APIResponse(
        data=DashboardAggregateResponse(
            user_id=user_id,
            stats=user_stats,
            topics=user_topics,
            difficulty=user_difficulty,
        )
    )

# ── User Stats ───────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/stats",
    response_model=APIResponse[UserStats],
    summary="Get user stats",
    description="Returns aggregate statistics: messages, consistency, streak, today's status. Publicly accessible without authentication.",
)
async def get_user_stats(user_id: str):
    # Public route — no auth required
    resolved = await _get_user_or_404(user_id)
    uid_int = resolved["user_id"]

    # Reuse existing handler logic — returns a rich dict
    report = await get_status_report(uid_int)

    return APIResponse(
        data=UserStats(
            user_id=user_id,
            total_messages=report["total_messages"],
            total_days_tracked=report["total_days_tracked"],
            days_posted=report["days_posted"],
            consistency_pct=report["consistency"],
            current_streak=report["current_streak"],
            longest_streak=report["longest_streak"],
            posted_today=report["posted_today"],
            today=report["today"],
            badges=report.get("badges", []),
        )
    )


# ── User Streak ──────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/streak",
    response_model=APIResponse[UserStreak],
    summary="Get user streak",
    description="Returns current and longest streak information. Publicly accessible without authentication.",
)
async def get_user_streak(user_id: str):
    # Public route — no auth required
    resolved = await _get_user_or_404(user_id)
    uid_int = resolved["user_id"]
    streak = await database.get_streak(uid_int)

    return APIResponse(
        data=UserStreak(
            user_id=user_id,
            current_streak=streak["current_streak"],
            longest_streak=streak["longest_streak"],
            last_post_date=streak.get("last_post_date"),
        )
    )


# ── User Topics ──────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/topics",
    response_model=APIResponse[UserTopics],
    summary="Get user topic analysis",
    description="Returns DSA topic frequency analysis for the user's progress logs. Publicly accessible without authentication.",
)
async def get_user_topics(user_id: str):
    # Public route — no auth required
    resolved = await _get_user_or_404(user_id)
    uid_int = resolved["user_id"]

    # Reuse existing handler logic
    topic_data = await get_topic_summary(uid_int)

    return APIResponse(
        data=UserTopics(
            user_id=user_id,
            total_mentions=topic_data["total_topics_mentioned"],
            unique_topics=topic_data["unique_topics"],
            frequency=[
                TopicFrequency(topic=t, count=c)
                for t, c in topic_data["frequency"]
            ],
        )
    )


# ── User Activity ────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/activity",
    response_model=APIResponse[UserActivityResponse],
    summary="Get recent user activity",
    description="Returns the user's latest progress logs. Owner-only: requires authentication and ownership. Raw message_content is private data.",
)
async def get_user_activity(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_user),
):
    # Owner-only — raw message_content is private. Fixes P2-02.
    _verify_owner(user_id, current_user)
    resolved = await _get_user_or_404(user_id, current_user)
    uid_int = resolved["user_id"]

    logs = await database.get_recent_progress_logs(uid_int, limit=limit)
    
    activity_logs = [
        ActivityLog(
            id=log["id"],
            posted_at=log["posted_at"],
            message_type=log["message_type"],
            message_content=log["message_content"],
            topics=log["topics"],
            parsed_fields=log["parsed_fields"],
        )
        for log in logs
    ]

    return APIResponse(
        data=UserActivityResponse(
            user_id=user_id,
            recent_logs=activity_logs,
        )
    )

@router.get(
    "/{user_id}/heatmap",
    response_model=APIResponse[HeatmapResponse],
    summary="Get user heatmap",
    description="Returns daily question counts for the past year. Publicly accessible without authentication.",
)
async def get_user_heatmap_route(user_id: str):
    # Public route — no auth required
    resolved = await _get_user_or_404(user_id)
    uid_int = resolved["user_id"]
    data = await database.get_user_heatmap(uid_int)
    return APIResponse(
        data=HeatmapResponse(
            user_id=user_id,
            dates=data["dates"],
            rest_dates=data.get("rest_dates", []),
            active_days=data["active_days"],
            current_streak=data["current_streak"],
            max_streak=data["max_streak"]
        )
    )



@router.get(
    "/{user_id}/difficulty",
    response_model=APIResponse[UserDifficulty],
    summary="Get user difficulty stats",
    description="Returns aggregate counts of easy, medium, hard problems. Publicly accessible without authentication.",
)
async def get_user_difficulty(user_id: str):
    # Public route — no auth required
    resolved = await _get_user_or_404(user_id)
    uid_int = resolved["user_id"]
    from handlers.summary_handler import get_difficulty_summary
    diff_data = await get_difficulty_summary(uid_int)
    
    return APIResponse(
        data=UserDifficulty(
            user_id=user_id,
            easy=diff_data["Easy"],
            medium=diff_data["Medium"],
            hard=diff_data["Hard"],
            expert=diff_data.get("Expert", 0),
            unknown=diff_data["Unknown"],
        )
    )


# ── Export Data ──────────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/export",
    summary="Export user progress logs",
    description="Returns a CSV file containing all progress logs for the user.",
)
async def export_user_data(user_id: str, current_user = Depends(get_current_user)):
    _verify_owner(user_id, current_user)
    resolved = await _get_user_or_404(user_id, current_user)
    uid_int = resolved["user_id"]
    
    from services.export_service import export_progress_csv
    filepath = await export_progress_csv(uid_int)
    
    if not os.path.exists(filepath):
        raise NotFoundError("Export file", filepath)
        
    return FileResponse(
        filepath, 
        media_type="text/csv", 
        filename=os.path.basename(filepath)
    )

