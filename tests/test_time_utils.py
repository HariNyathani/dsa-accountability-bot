"""
Unit tests for time utilities.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.time_utils import (
    is_consecutive,
    days_between,
    week_boundaries,
    parse_date,
)


def test_consecutive_dates():
    assert is_consecutive("2026-05-01", "2026-05-02") is True
    assert is_consecutive("2026-05-02", "2026-05-01") is True  # abs
    assert is_consecutive("2026-05-01", "2026-05-03") is False


def test_days_between():
    assert days_between("2026-05-01", "2026-05-01") == 0
    assert days_between("2026-05-01", "2026-05-08") == 7
    assert days_between("2026-05-08", "2026-05-01") == 7


def test_week_boundaries():
    from datetime import date
    start, end = week_boundaries(date(2026, 5, 6))  # Wednesday
    assert start == "2026-05-04"  # Monday
    assert end == "2026-05-10"  # Sunday


def test_parse_date():
    d = parse_date("2026-01-15")
    assert d.year == 2026
    assert d.month == 1
    assert d.day == 15


if __name__ == "__main__":
    test_consecutive_dates()
    test_days_between()
    test_week_boundaries()
    test_parse_date()
    print("✅ All time utility tests passed!")
