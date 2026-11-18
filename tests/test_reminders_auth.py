"""Reminder routes must require authentication and restrict access to the owner."""

import pytest

from api.middleware.auth import SessionUser, get_current_user


USER_ID = "123456789012345678"
OTHER_USER_ID = "987654321098765432"

ROUTES = [
    ("get", f"/reminders/{USER_ID}", None),
    ("post", "/reminders", {"user_id": USER_ID, "warn_time": "21:45"}),
    ("delete", f"/reminders/{USER_ID}", None),
]


async def _request(client, method, path, body):
    request = getattr(client, method)
    if body is None:
        return await request(path)
    return await request(path, json=body)


@pytest.mark.parametrize(("method", "path", "body"), ROUTES)
@pytest.mark.asyncio
async def test_reminder_routes_require_authentication(
    app, seeded_client, method, path, body
):
    app.dependency_overrides[get_current_user] = lambda: None
    try:
        response = await _request(seeded_client, method, path, body)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), ROUTES)
@pytest.mark.asyncio
async def test_reminder_routes_reject_other_users(
    app, seeded_client, method, path, body
):
    app.dependency_overrides[get_current_user] = lambda: SessionUser(
        id=OTHER_USER_ID, username="OtherUser"
    )
    try:
        response = await _request(seeded_client, method, path, body)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403


@pytest.mark.parametrize(("method", "path", "body"), ROUTES)
@pytest.mark.asyncio
async def test_reminder_routes_allow_owner(
    app, seeded_client, method, path, body
):
    app.dependency_overrides[get_current_user] = lambda: SessionUser(
        id=USER_ID, username="TestUser"
    )
    try:
        response = await _request(seeded_client, method, path, body)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
