"""
API endpoint tests.

Covers: health, status, users, leaderboard, analytics, summaries, reminders.
Uses a fresh, explicitly verified PostgreSQL test database from conftest.py.
"""

import pytest

from api.middleware.auth import SessionUser, get_current_user


def _authenticate_as(app, user_id: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: SessionUser(
        id=user_id, username="TestUser"
    )


# ── Health ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_status(client):
    r = await client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["api"] == "running"
    assert body["data"]["bot"] == "disabled"
    assert body["data"]["scheduler"] == "disabled"


@pytest.mark.asyncio
async def test_status_reflects_bot_and_scheduler_runtime(client):
    from api import runtime_status

    runtime_status.configure_bot(True)
    try:
        starting = (await client.get("/status")).json()["data"]
        assert starting["bot"] == "connecting"
        assert starting["scheduler"] == "stopped"

        runtime_status.set_bot_ready(True)
        runtime_status.set_scheduler_running(True)
        running = (await client.get("/status")).json()["data"]
        assert running["bot"] == "connected"
        assert running["scheduler"] == "running"
    finally:
        runtime_status.configure_bot(False)


# ── Users ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_empty(client):
    r = await client.get("/users")
    assert r.status_code == 200
    assert r.json()["data"] == []


@pytest.mark.asyncio
async def test_list_users_with_data(seeded_client):
    r = await seeded_client.get("/users")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) >= 1
    assert data[0]["user_id"] == "123456789012345678"


@pytest.mark.asyncio
async def test_get_user_404(client):
    r = await client.get("/users/12345")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_user(seeded_client):
    r = await seeded_client.get("/users/123456789012345678")
    assert r.status_code == 200
    assert r.json()["data"]["user_id"] == "123456789012345678"
    # Public unauthenticated profiles do not expose owner-only settings.
    assert r.json()["data"]["settings"] is None


@pytest.mark.asyncio
async def test_user_stats(seeded_client):
    r = await seeded_client.get("/users/123456789012345678/stats")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["user_id"] == "123456789012345678"
    assert "consistency_pct" in d


@pytest.mark.asyncio
async def test_user_streak(seeded_client):
    r = await seeded_client.get("/users/123456789012345678/streak")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["current_streak"] == 0


@pytest.mark.asyncio
async def test_user_topics(seeded_client):
    r = await seeded_client.get("/users/123456789012345678/topics")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["total_mentions"] == 0


# ── Leaderboard ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_leaderboard(seeded_client):
    r = await seeded_client.get("/leaderboard")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["total_users"] >= 1


@pytest.mark.asyncio
async def test_leaderboard_streaks(seeded_client):
    r = await seeded_client.get("/leaderboard/streaks")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_leaderboard_consistency(seeded_client):
    r = await seeded_client.get("/leaderboard/consistency")
    assert r.status_code == 200


# ── Analytics ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_overview(seeded_client):
    r = await seeded_client.get("/analytics/overview")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["total_users"] >= 1


@pytest.mark.asyncio
async def test_analytics_topics(seeded_client):
    r = await seeded_client.get("/analytics/topics")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_analytics_activity(seeded_client):
    r = await seeded_client.get("/analytics/activity?period=7d")
    assert r.status_code == 200


# ── Summaries ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summaries(seeded_client):
    r = await seeded_client.get("/summaries/123456789012345678")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["user_id"] == "123456789012345678"


@pytest.mark.asyncio
async def test_weekly_report(seeded_client):
    r = await seeded_client.get("/weekly-report/123456789012345678")
    assert r.status_code == 200
    assert r.json()["data"]["current_streak"] == 0
    assert r.json()["data"]["longest_streak"] == 0


@pytest.mark.asyncio
async def test_summaries_404(client):
    r = await client.get("/summaries/12345")
    assert r.status_code == 404


# ── Reminders ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_reminders(app, seeded_client):
    _authenticate_as(app, "123456789012345678")
    try:
        r = await seeded_client.get("/reminders/123456789012345678")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["deadline"] == "23:00"


@pytest.mark.asyncio
async def test_update_reminders(app, seeded_client):
    _authenticate_as(app, "123456789012345678")
    try:
        r = await seeded_client.post("/reminders", json={
            "user_id": "123456789012345678",
            "warn_time": "21:00",
            "deadline": "22:30",
        })
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["warn_time"] == "21:00"
    assert d["deadline"] == "22:30"


@pytest.mark.asyncio
async def test_delete_reminders(app, seeded_client):
    _authenticate_as(app, "123456789012345678")
    try:
        r = await seeded_client.delete("/reminders/123456789012345678")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert r.status_code == 200
    assert r.json()["data"]["reset"] is True


@pytest.mark.asyncio
async def test_reminders_404(app, client):
    _authenticate_as(app, "12345")
    try:
        r = await client.get("/reminders/12345")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert r.status_code == 404
