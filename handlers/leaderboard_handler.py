"""
Leaderboard handler — group ranking and stats.
"""

import logging
import discord
from db import database

logger = logging.getLogger("dsa_bot.leaderboard")

# Medal emojis for top 3
MEDALS = ["🥇", "🥈", "🥉"]

# Sort key definitions
SORT_KEYS = {
    "streak": ("current_streak", "🔥 Current Streak"),
    "longest": ("longest_streak", "🏆 Longest Streak"),
    "consistency": ("consistency", "📈 Consistency"),
    "posts": ("total_messages", "💬 Total Posts"),
    "days": ("days_posted", "📅 Days Posted"),
}


async def build_leaderboard(sort_by: str = "streak") -> discord.Embed:
    """
    Build a leaderboard embed.
    sort_by: 'streak' | 'longest' | 'consistency' | 'posts' | 'days'
    """
    result = await database.get_leaderboard_data()
    total_registered = result["total_registered_users"]
    data = result["rankings"]

    if not data:
        embed = discord.Embed(
            title="🏆 DSA Leaderboard",
            description="No registered users yet.\nUse `!register` to join!",
            color=0x95A5A6,
        )
        return embed

    # Determine sort
    sort_key, sort_title = SORT_KEYS.get(sort_by, SORT_KEYS["streak"])
    data.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    embed = discord.Embed(
        title="🏆 DSA Leaderboard",
        description=f"Sorted by: **{sort_title}**",
        color=0xF1C40F,
    )

    # Build ranking text (top 10 to stay within Discord's 1024-char field limit)
    lines = []
    for i, entry in enumerate(data[:10]):
        medal = MEDALS[i] if i < 3 else f"`{i+1}.`"
        username = entry.get("discord_username") or f"User {entry['user_id']}"

        # Truncate long usernames
        if len(username) > 20:
            username = username[:17] + "..."

        streak_emoji = "🔥" if entry["current_streak"] > 0 else "💤"
        line = (
            f"{medal} **{username}**\n"
            f"  {streak_emoji} Streak: **{entry['current_streak']}** "
            f"| Best: **{entry['longest_streak']}** "
            f"| Consistency: **{entry['consistency']}%** "
            f"| Posts: **{entry['total_messages']}**"
        )
        lines.append(line)

    embed.add_field(
        name="Rankings",
        value="\n\n".join(lines) if lines else "No data available.",
        inline=False,
    )

    # Footer with total stats
    active_streaks = len(data)
    embed.set_footer(
        text=f"👥 {total_registered} users tracked | 🔥 {active_streaks} active streaks | DSA Accountability Bot"
    )

    return embed


async def get_missed_today_report() -> list:
    """
    Get a list of users who haven't posted today.
    Useful for admin reporting.
    """
    from utils.time_utils import today_str
    today = today_str()
    users = await database.get_all_active_users_with_settings()

    missed = []
    for user in users:
        if user.get("tracked_channel_id"):
            user_tz = user.get("timezone", "")
            user_today = today_str(user_tz)
            if not await database.has_posted_today(user["user_id"], user_today):
                missed.append(user)

    return missed
