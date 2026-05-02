"""
Summary handler — weekly summary generation and on-demand reports.

Multi-user: generates summaries per user. The weekly scheduler iterates
over all active users.
"""

import logging
import discord
from collections import Counter
from datetime import timedelta

from db import database
from utils.time_utils import (
    now,
    today_str,
    last_week_boundaries,
    week_boundaries,
    month_boundaries,
    parse_date,
)
from utils.streak_utils import recalculate_streak
from services.ai_service import analyse_progress

logger = logging.getLogger("dsa_bot.summary_handler")


async def generate_weekly_summary_all(bot: discord.Client, send: bool = True):
    """
    Generate weekly summaries for ALL active users.
    Called by the weekly scheduler.
    """
    users = await database.get_all_active_users()
    for user in users:
        try:
            await generate_weekly_summary(
                bot, user_id=user["user_id"], send=send
            )
        except Exception as e:
            logger.error(
                f"Weekly summary failed for user {user['user_id']}: {e}",
                exc_info=True,
            )


async def generate_weekly_summary(
    bot: discord.Client,
    user_id: int = 0,
    send: bool = True,
) -> dict:
    """
    Generate and optionally send the weekly summary for a specific user.
    Called by the weekly scheduler or the !weekly command.
    """
    if not user_id:
        logger.warning("generate_weekly_summary called without user_id")
        return {}

    week_start, week_end = last_week_boundaries()

    # Get daily statuses for the week
    statuses = await database.get_daily_statuses_range(user_id, week_start, week_end)
    logs = await database.get_progress_logs(user_id, week_start, week_end)
    streak = await recalculate_streak(user_id)

    # Calculate stats
    days_posted = sum(1 for s in statuses if s["posted_flag"])
    total_days = 7
    days_missed = total_days - days_posted
    consistency = (days_posted / total_days) * 100 if total_days > 0 else 0
    total_messages = len(logs)

    # Collect topics
    all_topics = []
    for log in logs:
        if log.get("topics"):
            all_topics.extend(log["topics"].split(", "))
    topic_counts = Counter(all_topics)
    top_topics = topic_counts.most_common(5)

    # Save to DB
    await database.save_weekly_summary(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        days_posted=days_posted,
        days_missed=days_missed,
        consistency_percentage=round(consistency, 1),
        total_messages=total_messages,
    )

    summary = {
        "week_start": week_start,
        "week_end": week_end,
        "days_posted": days_posted,
        "days_missed": days_missed,
        "consistency": round(consistency, 1),
        "total_messages": total_messages,
        "current_streak": streak["current_streak"],
        "longest_streak": streak["longest_streak"],
        "top_topics": top_topics,
    }

    if send:
        embed = _build_summary_embed(summary)
        from services.discord_service import send_dm_embed
        await send_dm_embed(bot, user_id, embed)
        logger.info(f"Weekly summary sent to {user_id} for {week_start} to {week_end}")

    # Optional AI analysis
    import config
    if config.OPENAI_API_KEY and logs:
        analysis = await analyse_progress(logs, streak, consistency)
        if analysis and send:
            from services.discord_service import send_dm
            await send_dm(bot, user_id, f"🧠 **AI Weekly Analysis**\n\n{analysis}")

    return summary


async def get_status_report(user_id: int) -> dict:
    """Build a current-day status report."""
    user = await database.get_user(user_id)
    user_tz = user.get("timezone", "") if user else ""

    today = today_str(user_tz)
    posted = await database.has_posted_today(user_id, today)
    streak = await database.get_streak(user_id)
    total_messages = await database.get_message_count(user_id)

    # Overall consistency
    all_statuses = await database.get_all_daily_statuses(user_id)
    total_days = len(all_statuses)
    days_posted = sum(1 for s in all_statuses if s["posted_flag"])
    consistency = (days_posted / total_days) * 100 if total_days > 0 else 0

    return {
        "today": today,
        "posted_today": posted,
        "current_streak": streak["current_streak"],
        "longest_streak": streak["longest_streak"],
        "last_post_date": streak.get("last_post_date"),
        "total_messages": total_messages,
        "total_days_tracked": total_days,
        "days_posted": days_posted,
        "consistency": round(consistency, 1),
    }


async def get_topic_summary(user_id: int) -> dict:
    """Get topic frequency summary."""
    logs = await database.get_progress_logs(user_id)
    all_topics = []
    for log in logs:
        if log.get("topics"):
            all_topics.extend(log["topics"].split(", "))

    topic_counts = Counter(all_topics)
    return {
        "total_topics_mentioned": len(all_topics),
        "unique_topics": len(topic_counts),
        "frequency": topic_counts.most_common(),
    }


def _build_summary_embed(summary: dict) -> discord.Embed:
    """Build a rich Discord embed for the weekly summary."""
    consistency = summary["consistency"]

    # Color based on consistency
    if consistency >= 85:
        color = 0x2ECC71  # green
        grade = "🏆 Excellent!"
    elif consistency >= 70:
        color = 0xF1C40F  # yellow
        grade = "👍 Good"
    elif consistency >= 50:
        color = 0xE67E22  # orange
        grade = "⚠️ Needs Improvement"
    else:
        color = 0xE74C3C  # red
        grade = "🚨 Critical"

    embed = discord.Embed(
        title="📊 Weekly DSA Progress Summary",
        description=f"**{summary['week_start']}** → **{summary['week_end']}**",
        color=color,
    )

    embed.add_field(
        name="📅 Attendance",
        value=f"✅ Posted: **{summary['days_posted']}/7** days\n"
              f"❌ Missed: **{summary['days_missed']}** days",
        inline=True,
    )
    embed.add_field(
        name="📈 Consistency",
        value=f"**{consistency}%** — {grade}",
        inline=True,
    )
    embed.add_field(
        name="🔥 Streaks",
        value=f"Current: **{summary['current_streak']}** days\n"
              f"Longest: **{summary['longest_streak']}** days",
        inline=True,
    )
    embed.add_field(
        name="💬 Messages",
        value=f"**{summary['total_messages']}** this week",
        inline=True,
    )

    if summary.get("top_topics"):
        topics_text = "\n".join(
            f"• **{topic}** — {count}x" for topic, count in summary["top_topics"]
        )
        embed.add_field(name="📚 Top Topics", value=topics_text, inline=False)

    embed.set_footer(text="DSA Accountability Bot • Stay consistent! 💪")

    return embed
