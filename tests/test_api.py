"""
API endpoint tests.

Covers: health, status, users, leaderboard, analytics, summaries, reminders.
Uses the in-memory DB fixtures from conftest.py.
"""

import pytest


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
    assert data[0]["user_id"] == 999


@pytest.mark.asyncio
async def test_get_user_404(client):
    r = await client.get("/users/12345")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_user(seeded_client):
    r = await seeded_client.get("/users/999")
    assert r.status_code == 200
    assert r.json()["data"]["user_id"] == 999
    assert r.json()["data"]["settings"] is not None


@pytest.mark.asyncio
async def test_user_stats(seeded_client):
    r = await seeded_client.get("/users/999/stats")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["user_id"] == 999
    assert "consistency_pct" in d


@pytest.mark.asyncio
async def test_user_streak(seeded_client):
    r = await seeded_client.get("/users/999/streak")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["current_streak"] == 0


@pytest.mark.asyncio
async def test_user_topics(seeded_client):
    r = await seeded_client.get("/users/999/topics")
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
    r = await seeded_client.get("/summaries/999")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["user_id"] == 999


@pytest.mark.asyncio
async def test_weekly_report(seeded_client):
    r = await seeded_client.get("/weekly-report/999")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_summaries_404(client):
    r = await client.get("/summaries/12345")
    assert r.status_code == 404


# ── Reminders ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_reminders(seeded_client):
    r = await seeded_client.get("/reminders/999")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["deadline"] == "23:00"


@pytest.mark.asyncio
async def test_update_reminders(seeded_client):
    r = await seeded_client.post("/reminders", json={
        "user_id": 999,
        "warn_time": "21:00",
        "deadline": "22:30",
    })
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["warn_time"] == "21:00"
    assert d["deadline"] == "22:30"


@pytest.mark.asyncio
async def test_delete_reminders(seeded_client):
    r = await seeded_client.delete("/reminders/999")
    assert r.status_code == 200
    assert r.json()["data"]["reset"] is True


@pytest.mark.asyncio
async def test_reminders_404(client):
    r = await client.get("/reminders/12345")
    assert r.status_code == 404
