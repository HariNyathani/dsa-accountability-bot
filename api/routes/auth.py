"""
Discord OAuth2 authentication routes.

GET  /auth/login     — redirect user to Discord OAuth consent screen
GET  /auth/callback  — handle OAuth callback, exchange code for token, set session cookie
GET  /auth/me        — return current authenticated user (or 401)
POST /auth/logout    — clear session cookie
"""

import logging
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

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


# ── Login ────────────────────────────────────────────────────────────────────

@router.get("/login", summary="Redirect to Discord OAuth")
async def login():
    """Redirect the user to Discord's OAuth2 consent page."""
    params = {
        "client_id": config.DISCORD_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
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
