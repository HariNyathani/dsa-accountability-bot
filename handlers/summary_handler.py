"""
Summary handler — weekly summary generation and on-demand reports.

Multi-user: generates summaries per user. The weekly scheduler iterates
over all active users.
"""

import json
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
from utils.topic_extractor import TOPIC_PATTERNS

logger = logging.getLogger("dsa_bot.summary_handler")

# Build reverse lookup dynamically for alias resolution (built once at startup)
GLOBAL_ALIAS_MAP = {}
for canonical, aliases in TOPIC_PATTERNS.items():
    for alias in aliases:
        GLOBAL_ALIAS_MAP[alias.lower()] = canonical


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
    total_messages = sum(len(log.get("topics", "").split(", ")) if log.get("topics") else 0 for log in logs if log.get("message_type") != "plan")

    # Collect topics (exposure-based: prefer LeetCode tags from parsed_fields)
    all_topics = []
    for log in logs:
        if log.get("message_type") == "plan":
            continue
        all_topics.extend(_extract_exposure_topics(log))
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


def _calculate_badges(streak: int, total_messages: int) -> list:
    badges = []
    # Streak Badges
    if streak >= 1825: badges.append("💎 Mythic Ascendant (5 Years)")
    elif streak >= 365: badges.append("🔥 Unstoppable (365 Days)")
    elif streak >= 100: badges.append("💯 Century Club (100 Days)")
    elif streak >= 30: badges.append("⚡ On Fire (30 Days)")
    elif streak >= 10: badges.append("🌱 Warming Up (10 Days)")

    # Volume Badges
    if total_messages >= 1000: badges.append("🧠 Algorithm Master (1000+ Qs)")
    elif total_messages >= 500: badges.append("⚔️ Gladiator (500+ Qs)")
    elif total_messages >= 100: badges.append("🛠️ Builder (100+ Qs)")
    elif total_messages >= 50: badges.append("🎯 Focused (50+ Qs)")
    
    return badges


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
        "badges": _calculate_badges(streak["current_streak"], total_messages),
    }


def _extract_exposure_topics(log: dict) -> list:
    """
    Extract DSA topic tags from a single progress log for chart/frequency analytics.

    Priority:
      1. If parsed_fields contains 'log' entries with 'leetcode_topics', unpack
         those comma-separated official tags (exposure-based counting).
      2. Otherwise fall back to the legacy 'topics' column.

    This ensures charts show real DSA topics ("Array", "Hash Table") rather than
    problem titles ("Two Sum"), while legacy logs without LeetCode metadata
    continue to work.
    """
    topics = []
    from utils.topic_extractor import normalize_topic, STRICT_CANONICAL_TOPICS

    def _map_only(tags_list):
        return [normalize_topic(t) for t in tags_list if t.strip()]

    def _normalize_and_dedup(tags_list):
        seen = set()
        normalized = []
        for t in tags_list:
            if not t.strip():
                continue
            mapped = normalize_topic(t)
            if mapped not in seen:
                seen.add(mapped)
                normalized.append(mapped)
        return normalized

    pf_raw = log.get("parsed_fields")
    if pf_raw:
        try:
            pf = json.loads(pf_raw) if isinstance(pf_raw, str) else pf_raw
            log_entries = pf.get("log", [])
            for entry in log_entries:
                lc_topics = entry.get("leetcode_topics")
                if lc_topics:
                    q_count = entry.get("question_count", 1)
                    extracted_tags = [t.strip() for t in lc_topics.split(",") if t.strip()]
                    normalized_tags = _normalize_and_dedup(extracted_tags)
                    topics.extend(normalized_tags * q_count)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    # If we extracted LeetCode tags (which now includes manual tags), return directly
    if topics:
        return topics

    raw = log.get("topics", "")
    if raw:
        # Legacy strings already repeat the canonical topic `count` times
        raw_topics = [t.strip() for t in raw.split(",") if t.strip()]
        return _map_only(raw_topics)
    
    return []


async def get_topic_summary(user_id: int) -> dict:
    """Get topic frequency summary (exposure-based for charts)."""
    from utils.topic_extractor import STRICT_CANONICAL_TOPICS
    logs = await database.get_progress_logs(user_id)
    
    canonical_set = set(STRICT_CANONICAL_TOPICS)
    
    all_topics = []
    for log in logs:
        if log.get("message_type") in ("plan", "rest"):
            continue
        extracted = _extract_exposure_topics(log)
        filtered = [t for t in extracted if t in canonical_set]
        all_topics.extend(filtered)

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


async def get_difficulty_summary(user_id: int) -> dict:
    """Get difficulty distribution (Easy, Medium, Hard, Unknown)."""
    logs = await database.get_progress_logs(user_id)
    counts = {"Easy": 0, "Medium": 0, "Hard": 0, "Unknown": 0}
    for log in logs:
        if log.get("message_type") == "plan":
            continue
            
        pf_raw = log.get("parsed_fields")
        if pf_raw:
            try:
                pf = json.loads(pf_raw) if isinstance(pf_raw, str) else pf_raw
                log_entries = pf.get("log", [])
                for entry in log_entries:
                    q_count = entry.get("question_count", 1)
                    diff = entry.get("leetcode_difficulty")
                    if diff:
                        diff_title = diff.strip().title()
                        if diff_title in counts:
                            counts[diff_title] += q_count
                        else:
                            counts["Unknown"] += q_count
                    else:
                        counts["Unknown"] += q_count
            except:
                pass
        else:
            # Fallback for old logs
            topics_raw = log.get("topics", "")
            if topics_raw:
                raw_topics = [t.strip() for t in topics_raw.split(",") if t.strip()]
                counts["Unknown"] += len(raw_topics)

    return counts
