"""
Reusable FastAPI dependencies for HTTP cache headers.

`public_cache` sets ``Cache-Control: public, max-age=60`` on a response and is
intended for unauthenticated, read-only endpoints (leaderboard, analytics,
public profile pages, etc.).
"""

from fastapi import Response

PUBLIC_MAX_AGE = 60


def public_cache(response: Response):
    """Set ``Cache-Control: public, max-age=60`` on the outgoing response."""
    response.headers["Cache-Control"] = f"public, max-age={PUBLIC_MAX_AGE}"
    return response
