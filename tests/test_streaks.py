"""Streak calculations must use each user's configured local date."""

import pytest

from db import database
from utils import streak_utils


@pytest.mark.asyncio
async def test_recalculate_streak_uses_user_timezone(app, monkeypatch):
    user_id = 123456789012345681
    await database.register_user(
        user_id,
        discord_username="timezone-streak-test",
        timezone="America/Los_Angeles",
    )
    await database.mark_posted(user_id, "2026-01-01")

    def fixed_today(timezone_str=""):
        return "2026-01-02" if timezone_str == "America/Los_Angeles" else "2026-01-03"

    monkeypatch.setattr(streak_utils, "today_str", fixed_today)
    streak = await streak_utils.recalculate_streak(user_id)

    assert streak["current_streak"] == 1
    assert streak["longest_streak"] == 1
    assert streak["last_post_date"] == "2026-01-01"
