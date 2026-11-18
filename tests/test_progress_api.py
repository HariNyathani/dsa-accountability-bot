"""Authenticated progress API tests for date bounds and plan semantics."""

from datetime import timedelta

import pytest

from api.middleware.auth import create_session_token
from db import database
from utils.time_utils import parse_date, today_str


async def _register_and_authenticate(user_id: int, username: str) -> str:
    await database.register_user(user_id, discord_username=username, timezone="Asia/Kolkata")
    token = create_session_token({"id": str(user_id), "username": username})
    return f"Bearer {token}"


def _tomorrow() -> str:
    return (parse_date(today_str("Asia/Kolkata")) + timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_done_submission_rejects_future_date_without_logging(client):
    user_id = 123456789012345679
    authorization = await _register_and_authenticate(user_id, "future-date-test")

    response = await client.post(
        "/progress",
        headers={"Authorization": authorization},
        json={
            "intent_type": "done",
            "topics": [{"canonical_topic": "Arrays", "question_count": 1}],
            "target_date": _tomorrow(),
        },
    )

    assert response.status_code == 400
    assert "future" in response.json()["error"].lower()
    assert await database.get_progress_logs(user_id) == []
    assert await database.get_all_daily_statuses(user_id) == []


@pytest.mark.asyncio
async def test_plan_submission_is_not_counted_as_completed_progress(client):
    user_id = 123456789012345680
    authorization = await _register_and_authenticate(user_id, "plan-test")
    planned_date = _tomorrow()

    response = await client.post(
        "/progress",
        headers={"Authorization": authorization},
        json={
            "intent_type": "plan",
            "topics": [{"canonical_topic": "Arrays", "question_count": 2}],
            "target_date": planned_date,
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["msg_type"] == "plan"
    logs = await database.get_progress_logs(user_id)
    assert len(logs) == 1
    assert logs[0]["message_type"] == "plan"
    assert logs[0]["log_date"] == planned_date
    assert await database.get_daily_question_count(user_id, planned_date) == 0
    streak = await database.get_streak(user_id)
    assert streak["current_streak"] == 0
    assert streak["last_post_date"] is None
    assert await database.get_all_daily_statuses(user_id) == []
