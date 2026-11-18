"""Discord admin log commands delegate future-date checks to the user-aware service."""

import datetime as datetime_module
import importlib
import logging
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_sudo_log_does_not_reject_date_using_server_clock(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)
    bot_module = importlib.import_module("bot")

    real_datetime = datetime_module.datetime

    class FrozenDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 2)

    monkeypatch.setattr(datetime_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(bot_module, "_is_admin", lambda ctx: True)

    async def is_registered(user_id):
        return True

    calls = []

    async def process_submission(**kwargs):
        calls.append(kwargs)
        return {"status": "success", "feedback_message": "ok", "streak": {}}

    monkeypatch.setattr(bot_module.database, "is_registered", is_registered)
    monkeypatch.setattr(bot_module, "process_progress_submission", process_submission)

    sent = []

    async def send(message):
        sent.append(message)

    ctx = SimpleNamespace(
        author=SimpleNamespace(id=999),
        channel=SimpleNamespace(id=1),
        send=send,
    )
    command = bot_module.bot.get_command("sudo_log")
    await command.callback(ctx, args="<@123456789012345678> 2026-01-03 rest")

    assert len(calls) == 1
    assert calls[0]["override_date"] == "2026-01-03"
    assert sent and "2026-01-03" in sent[-1]
