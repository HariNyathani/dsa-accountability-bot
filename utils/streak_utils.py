"""
Streak calculation utilities.
"""

import logging
from datetime import timedelta
from utils.time_utils import parse_date, today_str, is_consecutive
from db import database

logger = logging.getLogger("dsa_bot.streak")


async def recalculate_streak(user_id: int) -> dict:
    """
    Recalculate current and longest streak from daily_status rows.
    Returns {"current_streak": int, "longest_streak": int, "last_post_date": str | None}.
    """
    statuses = await database.get_all_daily_statuses(user_id)

    posted_dates = sorted(
        [s["date"] for s in statuses if s["posted_flag"]],
    )

    if not posted_dates:
        await database.update_streak(user_id, 0, 0, "")
        return {"current_streak": 0, "longest_streak": 0, "last_post_date": None}

    # Walk through posted dates and compute streaks
    current = 1
    longest = 1
    for i in range(1, len(posted_dates)):
        if is_consecutive(posted_dates[i - 1], posted_dates[i]):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    last_post = posted_dates[-1]

    # If last post is not today or yesterday, current streak is 0
    today = today_str()
    today_date = parse_date(today)
    last_post_date = parse_date(last_post)
    diff = (today_date - last_post_date).days

    if diff > 1:
        current = 0
    # diff == 1 means yesterday — streak is still "alive" but not yet extended today
    # diff == 0 means today — streak includes today

    await database.update_streak(user_id, current, longest, last_post)
    return {
        "current_streak": current,
        "longest_streak": longest,
        "last_post_date": last_post,
    }


async def on_post(user_id: int, post_date: str) -> dict:
    """
    Called when a valid progress post is recorded.
    Updates streak based on the new post.
    Returns updated streak info.
    """
    streak = await database.get_streak(user_id)
    last = streak.get("last_post_date")
    current = streak["current_streak"]
    longest = streak["longest_streak"]

    if last and is_consecutive(last, post_date):
        current += 1
    elif last == post_date:
        # Already posted today — no change
        pass
    else:
        current = 1

    longest = max(longest, current)

    await database.update_streak(user_id, current, longest, post_date)
    logger.info(
        f"Streak updated for {user_id}: current={current}, longest={longest}"
    )
    return {
        "current_streak": current,
        "longest_streak": longest,
        "last_post_date": post_date,
    }
