"""Deployment blueprint must expose the database variable used by the app."""

import re
from pathlib import Path


def test_render_blueprint_declares_runtime_database_url():
    render_manifest = Path(__file__).resolve().parents[1] / "render.yaml"
    manifest = render_manifest.read_text(encoding="utf-8")

    assert re.search(r"(?m)^\s*- key: DATABASE_URL\s*$", manifest)
    assert not re.search(r"(?m)^\s*- key: DATABASE_PATH\s*$", manifest)
    for key in (
        "APP_ENV",
        "SESSION_SECRET",
        "COOKIE_SECURE",
        "FRONTEND_URL",
        "DISCORD_CLIENT_ID",
        "DISCORD_CLIENT_SECRET",
        "DISCORD_OAUTH_REDIRECT_URI",
        "DISCORD_OAUTH_MOBILE_REDIRECT_URI",
    ):
        assert re.search(rf"(?m)^\s*- key: {key}\s*$", manifest)

    assert re.search(r"(?m)^\s*- key: APP_ENV\n\s+value: production$", manifest)
    assert re.search(r"(?m)^\s*- key: COOKIE_SECURE\n\s+value: \"true\"$", manifest)
    assert re.search(r"(?m)^\s*- key: FRONTEND_URL\n\s+value: https://dsabot\.in$", manifest)
