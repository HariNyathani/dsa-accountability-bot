"""Thread-safe process-local state for bot and scheduler health reporting."""

from threading import Lock

_lock = Lock()
_bot_status = "disabled"
_scheduler_status = "disabled"


def configure_bot(enabled: bool) -> None:
    """Set whether this process is expected to run the Discord bot."""
    global _bot_status, _scheduler_status
    with _lock:
        if enabled:
            _bot_status = "connecting"
            _scheduler_status = "stopped"
        else:
            _bot_status = "disabled"
            _scheduler_status = "disabled"


def set_bot_ready(ready: bool) -> None:
    """Record Discord gateway readiness from the bot lifecycle events."""
    global _bot_status
    with _lock:
        if _bot_status != "disabled":
            _bot_status = "connected" if ready else "disconnected"


def set_scheduler_running(running: bool) -> None:
    """Record APScheduler's observed running state."""
    global _scheduler_status
    with _lock:
        if _bot_status != "disabled":
            _scheduler_status = "running" if running else "stopped"


def snapshot() -> tuple[str, str]:
    """Return a consistent (bot, scheduler) status snapshot."""
    with _lock:
        return _bot_status, _scheduler_status
