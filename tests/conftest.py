"""
Shared test fixtures for API testing.

Uses httpx.AsyncClient against the FastAPI test app with a
temporary file-based SQLite database so tests never touch production data.
"""

import os
import tempfile
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def app(tmp_path):
    """Create a fresh FastAPI app with a temporary file DB."""
    db_path = str(tmp_path / "test.db")
    os.environ["DATABASE_PATH"] = db_path

    # Patch the DB_PATH in the database module BEFORE init
    from db import database
    database.DB_PATH = db_path
    await database.init_db()

    from api.app import create_app
    application = create_app()
    yield application


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client bound to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded_client(app):
    """Client with a test user pre-registered in the database."""
    from db import database
    await database.register_user(
        user_id=999,
        discord_username="TestUser#0001",
        timezone="Asia/Kolkata",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
