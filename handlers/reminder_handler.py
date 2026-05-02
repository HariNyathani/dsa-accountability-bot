"""
Reminder handler — per-user scheduled checks.

Uses a single minutely ticker that checks ALL registered users against
their individual reminder schedules (in their own timezone).
Prevents duplicate reminders using daily_status flags.
"""

import logging
import discord

from db import database
from services.discord_service import send_dm
from services.email_service import send_reminder_email_to
from utils.time_utils import now as get_now, today_str

logger = logging.getLogger("dsa_bot.reminder_handler")


async def check_all_reminders(bot: discord.Client):
    """
    Called every minute by the scheduler.
    Iterates over all active users and checks if any reminder should fire
    based on their personal schedule and timezone.
    """
    users = await database.get_all_active_users_with_settings()

    for user in users:
        try:
            await _check_user_reminders(bot, user)
        except Exception as e:
            logger.error(
                f"Error checking reminders for user {user['user_id']}: {e}",
                exc_info=True,
            )


async def _check_user_reminders(bot: discord.Client, user: dict):
    """Check and fire reminders for a single user."""
    user_id = user["user_id"]
    user_tz = user.get("timezone", "")
    channel_id = user.get("tracked_channel_id", 0)

    # Skip users without a tracked channel
    if not channel_id:
        return

    current_time = get_now(user_tz)
    current_hour = current_time.hour
    current_minute = current_time.minute
    today = today_str(user_tz)

    # Already posted today? Skip all reminders.
    if await database.has_posted_today(user_id, today):
        return

    await database.ensure_daily_status(user_id, today)

    # Check warning reminder
    warn_h = user.get("warn_hour", 22)
    warn_m = user.get("warn_minute", 0)
    if current_hour == warn_h and current_minute == warn_m:
        if not await database.was_reminder_sent(user_id, today, "warn"):
            await _send_warn_reminder(bot, user_id, today)

    # Check final reminder
    final_h = user.get("final_hour", 23)
    final_m = user.get("final_minute", 0)
    if current_hour == final_h and current_minute == final_m:
        if not await database.was_reminder_sent(user_id, today, "final"):
            await _send_final_reminder(bot, user_id, today)

    # Check email escalation
    email_h = user.get("email_hour", 23)
    email_m = user.get("email_minute", 30)
    if current_hour == email_h and current_minute == email_m:
        if not await database.was_reminder_sent(user_id, today, "email"):
            await _send_email_escalation(bot, user_id, user, today)


async def _send_warn_reminder(bot: discord.Client, user_id: int, today: str):
    """Send warning DM."""
    message = (
        "⏰ **DSA Progress Reminder**\n\n"
        f"Hey! You haven't posted your DSA progress today ({today}).\n"
        "You still have time before the deadline.\n\n"
        "Post your progress in the DSA channel now! 💪\n"
        "Even a short update counts."
    )

    sent = await send_dm(bot, user_id, message)
    if sent:
        await database.mark_reminder_sent(user_id, today, "warn")
        logger.info(f"Warning DM sent to {user_id}")
    else:
        logger.error(f"Failed to send warning DM to {user_id}")


async def _send_final_reminder(bot: discord.Client, user_id: int, today: str):
    """Send final alert DM."""
    streak = await database.get_streak(user_id)
    current = streak.get("current_streak", 0)

    message = (
        "🚨 **FINAL DSA Progress Alert**\n\n"
        f"You STILL haven't posted your progress today ({today}).\n"
        "**The deadline has arrived!**\n\n"
    )

    if current > 0:
        message += (
            f"⚠️ Your **{current}-day streak** is about to break!\n"
            "Don't lose your momentum.\n\n"
        )

    message += (
        "Post ANYTHING in the DSA channel right now:\n"
        "• What you studied\n"
        "• Problems solved\n"
        "• Even \"reviewed notes today\"\n\n"
        "**Next: email escalation if still no post.**"
    )

    sent = await send_dm(bot, user_id, message)
    if sent:
        await database.mark_reminder_sent(user_id, today, "final")
        logger.info(f"Final DM sent to {user_id}")
    else:
        logger.error(f"Failed to send final DM to {user_id}")


async def _send_email_escalation(bot: discord.Client, user_id: int, user: dict, today: str):
    """Send email escalation + DM."""
    email = user.get("email", "")

    # Send email if configured
    email_sent = False
    if email:
        email_sent = send_reminder_email_to(today, email)

    # Also send a DM
    dm_message = (
        "📧🚨 **EMAIL ESCALATION SENT**\n\n"
        f"You missed the deadline for {today}.\n"
    )
    if email_sent:
        dm_message += "An escalation email has been sent to your inbox.\n\n"
    else:
        dm_message += "No email configured — set one with `!setemail <email>`.\n\n"
    dm_message += (
        "Your streak will reset at midnight unless you post NOW.\n"
        "Every day matters. Stay accountable! 🎯"
    )

    dm_sent = await send_dm(bot, user_id, dm_message)

    if email_sent or dm_sent:
        await database.mark_reminder_sent(user_id, today, "email")
        logger.info(f"Email escalation for {user_id}: email={email_sent}, dm={dm_sent}")
    else:
        logger.error(f"All escalation channels failed for {user_id}")


# ── Legacy compat wrappers (no longer used by bot.py, kept for safety) ───────

async def check_10pm(bot: discord.Client):
    """Legacy — now handled by check_all_reminders."""
    await check_all_reminders(bot)

async def check_11pm(bot: discord.Client):
    """Legacy — now handled by check_all_reminders."""
    pass

async def check_1130pm(bot: discord.Client):
    """Legacy — now handled by check_all_reminders."""
    pass
