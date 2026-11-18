"""OAuth state must bind Discord redirects to the browser transaction."""

from urllib.parse import parse_qs, urlsplit

import pytest

from api.routes import auth as auth_routes


class _TokenExchangeFailure:
    status_code = 400
    text = "stubbed OAuth exchange failure"


class _StubAsyncClient:
    def __init__(self):
        self.post_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, *args, **kwargs):
        self.post_calls += 1
        return _TokenExchangeFailure()


@pytest.mark.asyncio
@pytest.mark.parametrize("mobile", [False, True])
async def test_login_emits_transaction_state_and_http_only_cookie(mobile):
    response = await auth_routes.login(mobile=mobile)
    params = parse_qs(urlsplit(response.headers["location"]).query)
    state = params.get("state", [""])[0]
    cookie = response.headers.get("set-cookie", "")

    assert len(state) >= 32
    assert "dsa_oauth_state=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=600" in cookie


@pytest.mark.asyncio
@pytest.mark.parametrize("callback_path", ["/auth/callback", "/auth/mobile-callback"])
async def test_callback_rejects_unbound_state_before_code_exchange(
    client, monkeypatch, callback_path
):
    stub = _StubAsyncClient()
    monkeypatch.setattr(auth_routes.httpx, "AsyncClient", lambda **kwargs: stub)

    response = await client.get(f"{callback_path}?code=not-real&state=attacker-value")

    assert 300 <= response.status_code < 400
    assert "auth_error=state_mismatch" in response.headers["location"]
    assert stub.post_calls == 0


@pytest.mark.asyncio
async def test_matching_state_is_allowed_to_reach_stubbed_exchange(client, monkeypatch):
    stub = _StubAsyncClient()
    monkeypatch.setattr(auth_routes.httpx, "AsyncClient", lambda **kwargs: stub)

    login_response = await client.get("/auth/login")
    params = parse_qs(urlsplit(login_response.headers["location"]).query)
    state = params.get("state", [""])[0]
    assert state, "login must supply OAuth state before the callback can be tested"
    response = await client.get(f"/auth/callback?code=not-real&state={state}")

    assert 300 <= response.status_code < 400
    assert "auth_error=token_exchange_failed" in response.headers["location"]
    assert stub.post_calls == 1
