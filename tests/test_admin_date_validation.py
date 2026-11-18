"""Admin target dates must be checked against the target user's timezone."""

from fastapi import HTTPException
import pytest

from api.routes import admin
from utils import time_utils


def _fixed_today(timezone_str=""):
    if timezone_str == "Pacific/Kiritimati":
        return "2026-01-03"
    return "2026-01-02"


def test_admin_target_date_accepts_target_user_today(monkeypatch):
    monkeypatch.setattr(time_utils, "today_str", _fixed_today)

    assert admin._validate_target_date("2026-01-03", "Pacific/Kiritimati") == "2026-01-03"


def test_admin_target_date_rejects_day_after_target_user_today(monkeypatch):
    monkeypatch.setattr(time_utils, "today_str", _fixed_today)

    with pytest.raises(HTTPException) as exc_info:
        admin._validate_target_date("2026-01-04", "Pacific/Kiritimati")
    assert exc_info.value.status_code == 400
    assert "future" in str(exc_info.value.detail).lower()
