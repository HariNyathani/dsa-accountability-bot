"""
Discord OAuth2 authentication routes.

GET  /auth/login            — redirect user to Discord OAuth consent screen
GET  /auth/callback         — handle OAuth callback, exchange code for token, set session cookie
GET  /auth/mobile-callback  — handle OAuth callback for mobile; issues an opaque exchange code
POST /auth/exchange         — mobile app exchanges the short-lived code for the JWT (body, not URL)
GET  /auth/me               — return current authenticated user (or 401)
POST /auth/logout           — revoke JWT jti + clear session cookie

Security hardening (Module 4):
  P2-11 — OAuth state parameter: login generates a random state stored in a
           short-lived cookie; both callbacks verify it before proceeding.
  P2-06 — JWT never in URL: mobile-callback issues a random opaque exchange
           code (60-second TTL, single-use) and redirects with ?code=<opaque>.
           POST /auth/exchange redeems the code and returns the JWT in the
           JSON body only.
  P2-05 — Logout now revokes the token's jti in the revoked_tokens table so
           the token is dead immediately, not just cookie-deleted.
"""

import logging
import secrets
import time
from threading import Lock
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

import config
from api.middleware.auth import (
    create_session_token,
    get_current_user,
    revoke_token,
)

logger = logging.getLogger("dsa_bot.api.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])

DISCORD_API = "https://discord.com/api/v10"
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

# Scopes: identify gives us user id/username/avatar, no guilds needed
SCOPES = "identify"

# ── In-process exchange-code store (P2-06) ───────────────────────────────────
# Maps opaque_code -> {"jwt": str, "expires_at": float, "used": bool}
# Single-process only — acceptable per deployment model (one uvicorn worker).
_exchange_store: dict[str, dict] = {}
_exchange_lock = Lock()
_EXCHANGE_CODE_TTL = 60  # seconds


def _issue_exchange_code(jwt_token: str) -> str:
    """Store a JWT behind a random opaque code, return the code."""
    code = secrets.token_urlsafe(32)
    with _exchange_lock:
        # Prune expired codes to avoid unbounded growth
        now = time.time()
        expired = [k for k, v in _exchange_store.items() if v["expires_at"] < now]
        for k in expired:
            del _exchange_store[k]
        _exchange_store[code] = {
            "jwt": jwt_token,
            "expires_at": now + _EXCHANGE_CODE_TTL,
            "used": False,
        }
    return code


def _redeem_exchange_code(code: str) -> str | None:
    """Redeem an exchange code exactly once. Returns the JWT or None."""
    with _exchange_lock:
        entry = _exchange_store.get(code)
        if not entry:
            return None
        if entry["used"] or time.time() > entry["expires_at"]:
            return None
        entry["used"] = True
        return entry["jwt"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _redirect_uri() -> str:
    return config.DISCORD_OAUTH_REDIRECT_URI


def _mobile_redirect_uri() -> str:
    return config.DISCORD_OAUTH_MOBILE_REDIRECT_URI


# ── Login ────────────────────────────────────────────────────────────────────

@router.get("/login", summary="Redirect to Discord OAuth")
async def login(mobile: bool = False):
    """Redirect the user to Discord's OAuth2 consent page.

    Generates a random `state` value and stores it in a short-lived cookie
    so the callback can verify the request is legitimate (P2-11).
    When *mobile=true*, the redirect_uri points to the mobile-callback endpoint.
    """
    state = secrets.token_urlsafe(32)
    redirect_uri = _mobile_redirect_uri() if mobile else _redirect_uri()
    params = {
        "client_id": config.DISCORD_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    }
    url = f"{DISCORD_OAUTH_URL}?{urlencode(params)}"
    response = RedirectResponse(url)
    # Store state in a short-lived HttpOnly cookie (5 min TTL).
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=300,
        path="/",
    )
    return response


# ── OAuth Callback (web) ──────────────────────────────────────────────────────

@router.get("/callback", summary="Discord OAuth callback")
async def callback(code: str = None, state: str = None, request: Request = None):
    """
    Verify OAuth state, exchange the authorization code for a Discord access
    token, fetch the user profile, mint a JWT, and redirect the web frontend
    with a short-lived opaque exchange code as a query param.

    Module 9 (P2-04): The JWT is NO LONGER delivered in a session cookie.
    The frontend receives ?code=<opaque>&user_id=<id> and calls
    POST /auth/exchange to redeem the opaque code for the raw JWT, which it
    stores in localStorage and sends as an Authorization: Bearer header.
    """
    # P2-11: Verify the state parameter against the cookie.
    stored_state = request.cookies.get("oauth_state") if request else None
    if not state or not stored_state or state != stored_state:
        logger.warning("OAuth callback: state mismatch (possible login CSRF)")
        return RedirectResponse(
            url=f"{config.FRONTEND_URL}/?auth_error=state_mismatch"
        )
    if not code:
        return RedirectResponse(
            url=f"{config.FRONTEND_URL}/?auth_error=missing_code"
        )

    # 1. Exchange code for Discord access token
    token_data = {
        "client_id": config.DISCORD_CLIENT_ID,
        "client_secret": config.DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _redirect_uri(),
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            DISCORD_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_resp.status_code != 200:
            logger.error("Discord token exchange failed: %s", token_resp.text)
            return RedirectResponse(
                url=f"{config.FRONTEND_URL}/?auth_error=token_exchange_failed"
            )

        tokens = token_resp.json()
        access_token = tokens["access_token"]

        # 2. Fetch user profile from Discord
        user_resp = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_resp.status_code != 200:
            logger.error("Discord user fetch failed: %s", user_resp.text)
            return RedirectResponse(
                url=f"{config.FRONTEND_URL}/?auth_error=user_fetch_failed"
            )

        discord_user = user_resp.json()

    logger.info(
        "OAuth login successful: %s (%s)",
        discord_user.get("username"),
        discord_user.get("id"),
    )

    # 2.5. Provision the user in the database (idempotent).
    try:
        from db import database
        await database.register_user(
            int(discord_user["id"]),
            discord_user.get("username", ""),
            timezone=config.DEFAULT_TIMEZONE,
        )
        logger.info("User provisioned: %s", discord_user.get("id"))
    except Exception as e:
        logger.warning("register_user failed for %s: %s", discord_user.get("id"), e)

    # 3. Create JWT session token
    session_token = create_session_token(discord_user)

    # 4. Module 9 (P2-04): Do NOT set a session cookie — Bearer is the sole
    #    auth transport. Issue the same short-lived opaque exchange code used
    #    by the mobile path; redirect the web frontend with it as a query
    #    param. The frontend calls POST /auth/exchange, receives the JWT in a
    #    JSON body, stores it in localStorage, and attaches it as a Bearer
    #    header on all subsequent requests.
    exchange_code = _issue_exchange_code(session_token)
    user_id = discord_user["id"]
    redirect_url = f"{config.FRONTEND_URL}/?code={exchange_code}&user_id={user_id}"
    response = RedirectResponse(url=redirect_url, status_code=302)
    # Clear the state cookie — it is single-use; carries no session credential.
    response.delete_cookie(key="oauth_state", path="/")
    return response


# ── Mobile OAuth Callback ─────────────────────────────────────────────────────
# NOTE: Register https://dsabot.in/api/auth/mobile-callback in Discord Developer
# Portal → OAuth2 → Redirects.

@router.get("/mobile-callback", summary="Discord OAuth callback for mobile apps")
async def mobile_callback(
    code: str = None,
    state: str = None,
    request: Request = None,
):
    """
    Verify OAuth state, exchange the authorization code, provision the user,
    then issue a SHORT-LIVED opaque exchange code and redirect the mobile app
    via a deep link containing ?code=<opaque> (NOT the raw JWT). (P2-06)
    """
    # P2-11: Verify state
    stored_state = request.cookies.get("oauth_state") if request else None
    if not state or not stored_state or state != stored_state:
        logger.warning("Mobile OAuth callback: state mismatch (possible login CSRF)")
        return RedirectResponse(
            url=f"{config.FRONTEND_URL}/?auth_error=state_mismatch"
        )
    if not code:
        return RedirectResponse(
            url=f"{config.FRONTEND_URL}/?auth_error=missing_code"
        )

    # 1. Exchange code for Discord access token
    token_data = {
        "client_id": config.DISCORD_CLIENT_ID,
        "client_secret": config.DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _mobile_redirect_uri(),
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            DISCORD_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_resp.status_code != 200:
            logger.error("Discord token exchange failed (mobile): %s", token_resp.text)
            return RedirectResponse(
                url=f"{config.FRONTEND_URL}/?auth_error=token_exchange_failed"
            )

        tokens = token_resp.json()
        access_token = tokens["access_token"]

        user_resp = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_resp.status_code != 200:
            logger.error("Discord user fetch failed (mobile): %s", user_resp.text)
            return RedirectResponse(
                url=f"{config.FRONTEND_URL}/?auth_error=user_fetch_failed"
            )

        discord_user = user_resp.json()

    logger.info(
        "OAuth login successful (mobile): %s (%s)",
        discord_user.get("username"),
        discord_user.get("id"),
    )

    # 2.5. Provision user in DB
    try:
        from db import database
        await database.register_user(
            int(discord_user["id"]),
            discord_user.get("username", ""),
            timezone=config.DEFAULT_TIMEZONE,
        )
        logger.info("User provisioned (mobile): %s", discord_user.get("id"))
    except Exception as e:
        logger.warning(
            "register_user failed (mobile) for %s: %s", discord_user.get("id"), e
        )

    # 3. Create the JWT — but do NOT embed it in any URL.
    session_token = create_session_token(discord_user)

    # 4. Issue a short-lived opaque exchange code (P2-06).
    #    The raw JWT is stored server-side; only the opaque code goes in the URL.
    exchange_code = _issue_exchange_code(session_token)
    user_id = discord_user["id"]
    deep_link = f"dsabot://auth/callback?code={exchange_code}&user_id={user_id}"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<title>Returning to DSA Accountability…</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #000;
    color: #e0e0e0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 Oxygen, Ubuntu, Cantarell, sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    -webkit-font-smoothing: antialiased;
  }}
  .card {{
    background: #0d0d0d;
    border: 1px solid rgba(45, 212, 168, 0.12);
    border-radius: 20px;
    padding: 48px 36px;
    max-width: 360px;
    width: 90vw;
    text-align: center;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.6),
                0 0 80px rgba(45, 212, 168, 0.04);
  }}
  .icon-ring {{
    width: 64px; height: 64px;
    margin: 0 auto 28px;
    border-radius: 50%;
    background: rgba(45, 212, 168, 0.08);
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .spinner {{
    width: 28px; height: 28px;
    border: 2.5px solid rgba(45, 212, 168, 0.15);
    border-top-color: #2DD4A8;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  h1 {{
    font-size: 18px;
    font-weight: 700;
    color: #f5f5f5;
    letter-spacing: 0.3px;
    margin-bottom: 8px;
  }}
  .subtitle {{
    font-size: 14px;
    color: #888;
    line-height: 1.5;
    margin-bottom: 32px;
  }}
  .btn {{
    display: inline-block;
    background: #2DD4A8;
    color: #000;
    font-size: 15px;
    font-weight: 600;
    padding: 14px 32px;
    border-radius: 12px;
    text-decoration: none;
    transition: opacity 0.2s, transform 0.15s;
    opacity: 0;
    transform: translateY(6px);
  }}
  .btn:active {{ transform: scale(0.97); }}
  .btn.show {{
    opacity: 1;
    transform: translateY(0);
  }}
  .hint {{
    font-size: 12px;
    color: #555;
    margin-top: 16px;
    opacity: 0;
    transition: opacity 0.5s;
  }}
  .hint.show {{ opacity: 1; }}
</style>
</head>
<body>
<div class="card">
  <div class="icon-ring"><div class="spinner"></div></div>
  <h1>DSA Accountability</h1>
  <p class="subtitle">Redirecting you back to the app…</p>
  <a id="fallback-btn" class="btn" href="{deep_link}">Open App</a>
  <p id="hint" class="hint">Tap the button if you weren't redirected automatically.</p>
</div>
<script>
  // Attempt the deep link immediately via JS-initiated navigation.
  // The URL contains only an opaque exchange code — no JWT in the URL.
  window.location.href = "{deep_link}";

  // After 2.5s, reveal the manual fallback button + hint.
  setTimeout(function() {{
    document.getElementById('fallback-btn').classList.add('show');
    document.getElementById('hint').classList.add('show');
  }}, 2500);
</script>
</body>
</html>
"""
    response = HTMLResponse(
        content=html_content,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )
    # Clear the state cookie after use.
    response.delete_cookie(key="oauth_state", path="/")
    return response


# ── Exchange Code Redemption (mobile — P2-06) ─────────────────────────────────

class ExchangeRequest(BaseModel):
    code: str


@router.post("/exchange", summary="Exchange mobile auth code for JWT")
async def exchange_code(body: ExchangeRequest):
    """
    Mobile app calls this endpoint immediately after receiving the deep link.
    The opaque code is single-use, expires in 60 seconds, and the JWT is
    returned in the JSON body — never in a URL or redirect. (P2-06)
    """
    jwt_token = _redeem_exchange_code(body.code)
    if jwt_token is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid, expired, or already-used exchange code.",
        )
    return JSONResponse(content={"token": jwt_token})


# ── Current User ──────────────────────────────────────────────────────────────

@router.get("/me", summary="Get current authenticated user")
async def get_me(request: Request):
    """Return the current user's profile from the session cookie, or 401."""
    user = get_current_user(request)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"authenticated": False, "user": None},
        )

    # Build avatar URL
    avatar_url = None
    if user.avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}.png?size=128"

    # Look up vanity handle from the database
    from db.database import get_user
    db_user = await get_user(int(user.id))
    profile_handle = db_user.get("username") if db_user else None

    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "profile_handle": profile_handle,
            "avatar": user.avatar,
            "avatar_url": avatar_url,
            "discriminator": user.discriminator,
            "is_admin": bool(config.ADMIN_DISCORD_ID) and str(user.id) == str(config.ADMIN_DISCORD_ID),
        },
    }


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", summary="Revoke JWT and clear session")
async def logout(request: Request):
    """
    Revoke the current token's jti in the revoked_tokens table so the JWT is
    dead immediately (not just client-deleted). (P2-05 / Module 9)

    Module 9 (P2-04): Auth is Bearer-header only; there are no session cookies
    to clear. The client discards the JWT from its own storage after this call.
    """
    user = get_current_user(request)
    if user and user.jti:
        try:
            await revoke_token(user.jti)
            logger.info("Token revoked: jti=%s user=%s", user.jti, user.id)
        except Exception as e:
            logger.error("Failed to revoke token jti=%s: %s", user.jti, e)

    return JSONResponse(content={"success": True, "message": "Logged out"})
