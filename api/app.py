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

from api.middleware.error_handler import register_error_handlers
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
        await db.init_db()
        health.set_start_time(time.time())
        logger.info("API started — database initialised, routes registered.")
        yield
        logger.info("API shutting down.")

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
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://dsabot.in", "https://www.dsabot.in"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request logging ──────────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

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
