"""
FastAPI application factory.

Creates and configures the app with all routes, middleware, and lifecycle hooks.
Import create_app() from here to get a fully configured ASGI application.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from api.middleware.error_handler import register_error_handlers
from api.middleware.ratelimit import RateLimitMiddleware
from api.middleware.request_logger import RequestLoggingMiddleware
from api.routes import health, users, leaderboard, analytics, summaries, reminders, auth, progress, admin

logger = logging.getLogger("dsa_bot.api")

API_VERSION = "1.0.0"


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Startup / shutdown lifecycle."""
        from db import database as db
        db.db_manager.init_pool()
        await db.init_db()
        health.set_start_time(time.time())
        logger.info("API started — database initialised, routes registered.")
        yield
        logger.info("API shutting down.")

    # ── Module 10 (P2-10): Gate OpenAPI docs behind ENVIRONMENT ──────────
    # In production the full API schema must not be exposed to anonymous
    # users — it leaks every endpoint, parameter, and admin operation.
    # Setting *_url=None tells FastAPI to return 404 for those paths.
    # In development/staging the standard URLs remain for local tooling.
    import config as _cfg
    IS_PROD = _cfg.ENVIRONMENT in ("production", "prod")

    app = FastAPI(
        title="DSA Accountability Bot — REST API",
        description=(
            "Production REST API exposing the DSA Accountability Bot's data layer.\n\n"
            "Provides user management, leaderboard rankings, analytics, "
            "weekly summaries, and reminder configuration — "
            "all powered by the same async database and services "
            "that drive the Discord bot."
        ),
        version=API_VERSION,
        # Docs disabled in production (P2-10 / Module 10).
        # Set ENVIRONMENT=development to re-enable for local work.
        docs_url=None if IS_PROD else "/docs",
        redoc_url=None if IS_PROD else "/redoc",
        openapi_url=None if IS_PROD else "/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    # Module 9 (P2-04): allow_credentials=False because auth is Bearer-header
    # only — there are no session cookies to be auto-attached by browsers.
    # allow_origins is driven by CORS_ALLOWED_ORIGINS (comma-separated, set in
    # .env / Railway) so the boundary can be tightened without a code deploy.
    import os as _os
    _cors_env = _os.getenv("CORS_ALLOWED_ORIGINS", "")
    _cors_origins = (
        [o.strip() for o in _cors_env.split(",") if o.strip()]
        if _cors_env
        else ["http://localhost:3000", "https://dsabot.in", "https://www.dsabot.in"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=False,   # No cookies — Bearer-only (P2-04 / Module 9)
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request logging ──────────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ── Rate limiting ─────────────────────────────────────────────────────
    # Fixed-window limits: OAuth 10/min/IP, Expensive 30/min/IP, Revision 60/hr/user.
    # Tune via env: RLIMIT_OAUTH_REQUESTS, RLIMIT_EXPENSIVE_REQUESTS, etc.
    app.add_middleware(RateLimitMiddleware)

    # ── GZip compression ─────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # ── Error handlers ───────────────────────────────────────────────────
    register_error_handlers(app)

    # ── Routes ───────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(leaderboard.router)
    app.include_router(analytics.router)
    app.include_router(summaries.router)
    app.include_router(reminders.router)
    app.include_router(progress.router)
    app.include_router(admin.router)

    return app
