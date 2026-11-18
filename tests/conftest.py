"""Shared API fixtures; database tests require an explicitly isolated target."""

import os
import re

import psycopg2
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from psycopg2.extensions import parse_dsn


_DISPOSABLE_DB_NAME = re.compile(r"^dsa_test_[0-9]{14}_[0-9a-f]{8}$")


@pytest.fixture(scope="session")
def isolated_test_database_url():
    """Fail closed unless the server confirms a fresh, uniquely named test DB."""
    test_db = os.getenv("TEST_DATABASE_URL")
    expected_name = os.getenv("TEST_DATABASE_NAME", "")
    if not test_db or not _DISPOSABLE_DB_NAME.fullmatch(expected_name):
        raise RuntimeError(
            "API tests require TEST_DATABASE_URL and a generated TEST_DATABASE_NAME"
        )

    try:
        declared_name = parse_dsn(test_db).get("dbname")
    except Exception:
        raise RuntimeError("refusing API tests: invalid test database DSN") from None
    if declared_name != expected_name:
        raise RuntimeError("refusing API tests: DSN does not match generated test database")

    conn = None
    try:
        conn = psycopg2.connect(test_db)
        with conn.cursor() as cur:
            cur.execute("BEGIN TRANSACTION READ ONLY")
            cur.execute("SELECT current_database()")
            identity_row = cur.fetchone()
            actual_name = identity_row[0] if identity_row else None
            if actual_name != expected_name or not _DISPOSABLE_DB_NAME.fullmatch(actual_name or ""):
                raise RuntimeError("refusing API tests: server database identity mismatch")
            cur.execute(
                "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
            )
            table_count_row = cur.fetchone()
            if table_count_row is None or table_count_row[0] != 0:
                raise RuntimeError("refusing API tests: generated test database is not empty")
        conn.rollback()
    except RuntimeError:
        if conn is not None:
            conn.rollback()
        raise
    except Exception:
        if conn is not None:
            conn.rollback()
        raise RuntimeError("refusing API tests: could not verify database target") from None
    finally:
        if conn is not None:
            conn.close()

    return test_db


@pytest_asyncio.fixture
async def app(isolated_test_database_url):
    """Create a FastAPI test app after database identity is verified."""
    test_db = isolated_test_database_url
    os.environ["DATABASE_URL"] = test_db

    # Patch the DSN in the database manager BEFORE init
    from db import database
    database.db_manager.dsn = test_db
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
        user_id=123456789012345678,
        discord_username="TestUser#0001",
        timezone="Asia/Kolkata",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
