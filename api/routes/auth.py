"""
Discord OAuth2 authentication routes.

GET  /auth/login            — redirect user to Discord OAuth consent screen
GET  /auth/callback         — handle OAuth callback, exchange code for token, set session cookie
GET  /auth/mobile-callback  — handle OAuth callback for mobile apps, redirect via deep link
GET  /auth/me               — return current authenticated user (or 401)
POST /auth/logout           — clear session cookie
"""

import logging
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import config
from api.middleware.auth import create_session_token, get_current_user

logger = logging.getLogger("dsa_bot.api.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])

DISCORD_API = "https://discord.com/api/v10"
DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

# Scopes: identify gives us user id/username/avatar, no guilds needed
SCOPES = "identify"


def _redirect_uri() -> str:
    """Build the OAuth2 callback URL from config."""
    return config.DISCORD_OAUTH_REDIRECT_URI


def _mobile_redirect_uri() -> str:
    """Build the mobile OAuth2 callback URL from config."""
    return config.DISCORD_OAUTH_MOBILE_REDIRECT_URI


# ── Login ────────────────────────────────────────────────────────────────────

@router.get("/login", summary="Redirect to Discord OAuth")
async def login(mobile: bool = False):
    """Redirect the user to Discord's OAuth2 consent page.

    When *mobile=true*, the redirect_uri points to the mobile-callback
    endpoint which returns a deep link instead of setting a cookie.
    """
    redirect_uri = _mobile_redirect_uri() if mobile else _redirect_uri()
    params = {
        "client_id": config.DISCORD_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
    }
    url = f"{DISCORD_OAUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)


# ── OAuth Callback ───────────────────────────────────────────────────────────

@router.get("/callback", summary="Discord OAuth callback")
async def callback(code: str, request: Request):
    """
    Exchange the authorization code for an access token,
    fetch the Discord user profile, create a JWT session cookie,
    and redirect to the frontend dashboard.
    """
    # 1. Exchange code for access token
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

    # 3. Create JWT session token
    session_token = create_session_token(discord_user)

    # 4. Redirect to frontend with session cookie set
    response = RedirectResponse(url=f"{config.FRONTEND_URL}/", status_code=302)
    response.set_cookie(
        key="dsa_session",
        value=session_token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/",
    )
    return response


# ── Mobile OAuth Callback ────────────────────────────────────────────────────
# NOTE: You must register https://dsabot.in/api/auth/mobile-callback as an
# additional redirect URI in the Discord Developer Portal → OAuth2 → Redirects.


@router.get("/mobile-callback", summary="Discord OAuth callback for mobile apps")
async def mobile_callback(code: str):
    """
    Exchange the authorization code for an access token,
    fetch the Discord user profile, create a JWT, and redirect to the
    mobile app via the dsabot:// custom URI scheme deep link.
    """
    # 1. Exchange code for access token
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

        # 2. Fetch user profile from Discord
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

    # 3. Create JWT session token
    session_token = create_session_token(discord_user)

    # 4. Hand off to the mobile app via deep link.
    #
    # Chrome on Android blocks HTTP 302 redirects to custom URI schemes
    # (dsabot://). Instead, we serve an HTML intermediary page that uses
    # JavaScript window.location.href — which Chrome DOES permit — to
    # trigger the deep link intent. A tappable fallback button is shown
    # if the automatic redirect doesn't fire within a few seconds.
    user_id = discord_user["id"]
    deep_link = f"dsabot://auth/callback?token={session_token}&user_id={user_id}"

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
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
    return HTMLResponse(content=html_content)


# ── Current User ─────────────────────────────────────────────────────────────

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


# ── Logout ───────────────────────────────────────────────────────────────────

@router.post("/logout", summary="Clear session and log out")
async def logout():
    """Clear the session cookie."""
    response = JSONResponse(content={"success": True, "message": "Logged out"})
    response.delete_cookie(
        key="dsa_session",
        path="/",
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
    )
    return response
