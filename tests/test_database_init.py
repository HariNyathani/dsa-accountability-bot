"""Database initialization must never delete user progress as a side effect."""

import asyncio

import pytest

from db import database
from utils.time_utils import now_iso, today_str


@pytest.mark.asyncio
async def test_init_db_applies_revision_bank_schema(app):
    """Fresh application startup creates the schema required by current writers."""

    def read_schema_state():
        with database.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'progress_logs'
                          AND column_name = 'is_review'
                    ), to_regclass('public.revision_bank') IS NOT NULL
                    """
                )
                row = cur.fetchone()
                if row is None:
                    raise AssertionError("schema query returned no row")
                return row

    has_review_column, has_revision_bank = await asyncio.to_thread(read_schema_state)
    assert has_review_column is True
    assert has_revision_bank is True


@pytest.mark.asyncio
async def test_init_db_preserves_legacy_topic_rows(app):
    """Legacy topic labels remain historical data across application startup."""
    user_id = 100000000000000001
    await database.register_user(user_id, discord_username="test-preserve-init")

    for index, topic in enumerate(("Uncategorized", "123.4")):
        await database.save_progress_log(
            user_id=user_id,
            channel_id=0,
            message_content=f"test record {index}",
            topics=topic,
            posted_at=now_iso(),
            log_date=today_str(),
            message_type="done",
            parsed_fields="{}",
            platform="leetcode",
        )

    await database.init_db()

    persisted_logs = await database.get_progress_logs(user_id)
    assert {row["topics"] for row in persisted_logs} == {"Uncategorized", "123.4"}
