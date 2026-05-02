"""
Timezone-aware datetime helpers.

Supports per-user timezones. Falls back to config.DEFAULT_TIMEZONE.
"""

from datetime import datetime, date, timedelta
from typing import Optional
import pytz
import config

_default_tz = pytz.timezone(config.DEFAULT_TIMEZONE)


def get_tz(timezone_str: str = "") -> pytz.BaseTzInfo:
    """Get a pytz timezone object, falling back to the default."""
    if timezone_str:
        try:
            return pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            pass
    return _default_tz


def now(timezone_str: str = "") -> datetime:
    """Current datetime in the given (or default) timezone."""
    return datetime.now(get_tz(timezone_str))


def today_str(timezone_str: str = "") -> str:
    """Today's date as YYYY-MM-DD string in local timezone."""
    return now(timezone_str).strftime("%Y-%m-%d")


def now_iso(timezone_str: str = "") -> str:
    """Current datetime as ISO-8601 string."""
    return now(timezone_str).isoformat()


def parse_date(date_str: str) -> date:
    """Parse a YYYY-MM-DD string into a date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def week_boundaries(reference: Optional[date] = None):
    """
    Return (week_start, week_end) as YYYY-MM-DD strings.
    Week starts on Monday.
    """
    ref = reference or now().date()
    start = ref - timedelta(days=ref.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def last_week_boundaries():
    """Return (start, end) for the previous week."""
    ref = now().date() - timedelta(days=7)
    return week_boundaries(ref)


def month_boundaries(reference: Optional[date] = None):
    """Return (month_start, month_end) as YYYY-MM-DD strings."""
    ref = reference or now().date()
    start = ref.replace(day=1)
    # last day of month
    if ref.month == 12:
        end = ref.replace(year=ref.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = ref.replace(month=ref.month + 1, day=1) - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def days_between(date1_str: str, date2_str: str) -> int:
    """Number of days between two YYYY-MM-DD dates."""
    d1 = parse_date(date1_str)
    d2 = parse_date(date2_str)
    return abs((d2 - d1).days)


def is_consecutive(date1_str: str, date2_str: str) -> bool:
    """Check if date2 is exactly 1 day after date1."""
    return days_between(date1_str, date2_str) == 1
