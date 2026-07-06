"""
In-memory rate-limiting middleware for FastAPI.

Implements a fixed-window counter keyed by either:
  - Client IP address  (for unauthenticated public endpoints)
  - Authenticated user ID from the Bearer/cookie JWT (for user-scoped limits)

Each endpoint can opt into a named limit group by including a custom request
header ``X-RateLimit-Group: <group>`` that the route sets via a FastAPI
dependency (see the ``rate_limit()`` helper below).

Limit groups are configured via environment variables:
    RLIMIT_<GROUP>_REQUESTS   — max requests in the window (default 30)
    RLIMIT_<GROUP>_WINDOW     — window duration in seconds (default 60)

Built-in groups (defaults match the implementation plan):
    OAUTH       — 10 req / 60 s / IP  (P2-08)
    EXPENSIVE   — 30 req / 60 s / IP  (P2-09)
    REVISION    — 60 req / 3600 s / user  (P3-03)

Architecture note: single-process / single-worker deployment.
If multi-worker is ever introduced, replace this with Redis-backed limits.
"""

import logging
import os
import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("dsa_bot.api.ratelimit")

# ── Group configuration ───────────────────────────────────────────────────────

def _group_cfg(group: str, default_req: int, default_window: int) -> tuple[int, int]:
    """Read RLIMIT_<GROUP>_REQUESTS and RLIMIT_<GROUP>_WINDOW from env."""
    g = group.upper()
    req = int(os.getenv(f"RLIMIT_{g}_REQUESTS", str(default_req)))
    win = int(os.getenv(f"RLIMIT_{g}_WINDOW", str(default_window)))
    return req, win


# (max_requests, window_seconds)
_GROUPS: dict[str, tuple[int, int]] = {
    "OAUTH":     _group_cfg("OAUTH",     10,  60),    # 10 / min / IP
    "EXPENSIVE": _group_cfg("EXPENSIVE", 30,  60),    # 30 / min / IP
    "REVISION":  _group_cfg("REVISION",  60, 3600),   # 60 / hour / user
}

# ── In-memory state: {group -> {key -> [window_start, count]}} ───────────────

_state: dict[str, dict[str, list]] = defaultdict(dict)
_lock = Lock()


def _check_limit(group: str, key: str) -> tuple[bool, int]:
    """
    Fixed-window counter. Returns (allowed, retry_after_seconds).
    allowed=True  → request is within limit.
    allowed=False → limit exceeded; retry_after is seconds until window resets.
    """
    max_req, window = _GROUPS[group]
    now = time.time()

    with _lock:
        entry = _state[group].get(key)
        if entry is None or now - entry[0] >= window:
            # New window
            _state[group][key] = [now, 1]
            return True, 0

        window_start, count = entry
        if count < max_req:
            entry[1] += 1
            return True, 0
        else:
            retry_after = int(window - (now - window_start)) + 1
            return False, retry_after


# ── Path → group mapping ──────────────────────────────────────────────────────

# Each tuple: (path_prefix, method_or_None, group, key_type)
#   key_type = "ip"   → keyed by client IP
#   key_type = "user" → keyed by authenticated user_id from JWT

_ROUTE_LIMITS: list[tuple[str, str | None, str, str]] = [
    # OAuth endpoints (P2-08)
    ("/auth/login",            None,   "OAUTH",     "ip"),
    ("/auth/callback",         None,   "OAUTH",     "ip"),
    ("/auth/mobile-callback",  None,   "OAUTH",     "ip"),
    ("/auth/exchange",         "POST", "OAUTH",     "ip"),
    # Expensive unauthenticated data endpoints (P2-09)
    ("/analytics/topics",      "GET",  "EXPENSIVE", "ip"),
    ("/analytics/overview",    "GET",  "EXPENSIVE", "ip"),
    ("/analytics/activity",    "GET",  "EXPENSIVE", "ip"),
    # Revision review — per authenticated user (P3-03)
    ("/progress/revision/review", "POST", "REVISION", "user"),
]


# Number of trusted reverse proxies in front of the app (Nginx = 1).
# Nginx's `proxy_add_x_forwarded_for` APPENDS the real peer to the RIGHT of
# X-Forwarded-For, so the trustworthy client IP is `_TRUSTED_PROXY_HOPS` entries
# from the right. Everything to the LEFT is client-supplied and spoofable.
_TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS", "1"))


def _client_ip(request: Request) -> str:
    """Resolve the real client IP without trusting spoofable header values.

    Taking the FIRST X-Forwarded-For entry let an attacker rotate the header to
    mint a fresh rate-limit bucket per request. We instead take the entry our
    OWN proxy appended (from the right), which the client cannot control.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= _TRUSTED_PROXY_HOPS:
            return parts[-_TRUSTED_PROXY_HOPS]
    # No / malformed XFF — fall back to the direct socket peer (unspoofable).
    if request.client:
        return request.client.host
    return "unknown"


def _authed_user_id(request: Request) -> str | None:
    """Extract user_id from a valid Bearer JWT. Bearer-only — no cookie fallback
    (Module 9 / P2-04). Cookies are not an accepted credential transport."""
    try:
        from api.middleware.auth import decode_session_token, _BEARER_PREFIX
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith(_BEARER_PREFIX):
            return None
        token = auth_header[len(_BEARER_PREFIX):]
        user = decode_session_token(token)
        if user:
            return str(user.id)
    except Exception:
        pass
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply fixed-window rate limits to matched routes."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method.upper()

        for (prefix, req_method, group, key_type) in _ROUTE_LIMITS:
            if not path.startswith(prefix):
                continue
            if req_method is not None and method != req_method:
                continue

            # Determine the rate-limit key
            if key_type == "user":
                uid = _authed_user_id(request)
                if uid is None:
                    # Not authenticated — let auth middleware handle 401
                    break
                key = f"user:{uid}"
            else:
                key = f"ip:{_client_ip(request)}"

            allowed, retry_after = _check_limit(group, key)
            if not allowed:
                logger.warning(
                    "Rate limit exceeded: group=%s key=%s path=%s",
                    group, key, path,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "Too many requests",
                        "detail": f"Rate limit exceeded. Retry after {retry_after}s.",
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            break  # matched and allowed — no need to check further rules

        return await call_next(request)
