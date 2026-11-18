"""Production authentication configuration fails closed on unsafe defaults."""

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _import_config(**overrides):
    env = os.environ.copy()
    for key in ("APP_ENV", "SESSION_SECRET", "COOKIE_SECURE"):
        env.pop(key, None)
    env.update(
        {
            "APP_ENV": "production",
            "PYTHON_DOTENV_DISABLED": "1",
            "PYTHONPATH": str(PROJECT_ROOT),
        }
    )
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "-c", "import config"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_rejects_missing_session_secret():
    result = _import_config(COOKIE_SECURE="true")
    assert result.returncode != 0
    assert "SESSION_SECRET" in result.stderr


def test_production_rejects_development_session_secret():
    result = _import_config(
        SESSION_SECRET="change-me-to-a-random-secret-key",
        COOKIE_SECURE="true",
    )
    assert result.returncode != 0
    assert "SESSION_SECRET" in result.stderr


def test_production_rejects_insecure_cookies():
    result = _import_config(
        SESSION_SECRET="test-only-session-secret-not-a-real-credential",
        COOKIE_SECURE="false",
    )
    assert result.returncode != 0
    assert "COOKIE_SECURE" in result.stderr


def test_production_accepts_configured_secret_and_secure_cookies():
    result = _import_config(
        SESSION_SECRET="test-only-session-secret-not-a-real-credential",
        COOKIE_SECURE="true",
    )
    assert result.returncode == 0, result.stderr
