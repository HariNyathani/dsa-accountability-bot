"""
Message handler — processes incoming Discord messages for DSA progress tracking.

Multi-user: checks if the message author is a registered user who tracks this
channel. If so, logs their progress. Otherwise, silently ignores.
"""

import logging
import discord

from db import database
from utils.time_utils import today_str, now_iso
from utils.topic_extractor import extract_topics, topics_to_str
from utils.streak_utils import on_post

logger = logging.getLogger("dsa_bot.message_handler")


async def handle_message(message: discord.Message, bot: discord.Client):
    """
    Called for every message the bot sees.
    Checks if the author is a registered user tracking this channel.
    """
    # Ignore bots
    if message.author.bot:
        return

    # Look up whether this user is registered AND tracking this channel
    user = await database.get_user_with_settings(message.author.id)
    if not user:
        return
    if not user.get("is_active"):
        return
    if user.get("tracked_channel_id") != message.channel.id:
        return

    content = message.content.strip()
    if not content:
        return

    # Use the user's timezone for date calculations
    user_tz = user.get("timezone", "")
    today = today_str(user_tz)
    now = now_iso(user_tz)

    # Anti-duplicate: skip if identical message already logged today
    if await database.check_duplicate_log(message.author.id, content, today):
        logger.debug(f"Duplicate message skipped for user {message.author.id}")
        return

    # Determine message type
    msg_type = _classify_message(content)

    # Extract topics
    topics = extract_topics(content)
    topics_str = topics_to_str(topics)

    # Save progress log
    await database.save_progress_log(
        user_id=message.author.id,
        channel_id=message.channel.id,
        message_content=content,
        topics=topics_str,
        posted_at=now,
        log_date=today,
        message_type=msg_type,
    )

    # Mark today as posted
    await database.mark_posted(message.author.id, today)

    # Update streak
    streak = await on_post(message.author.id, today)

    # React to confirm tracking
    try:
        if msg_type == "plan":
            await message.add_reaction("📋")
        elif msg_type == "done":
            await message.add_reaction("✅")
        else:
            await message.add_reaction("🔥")
    except discord.HTTPException:
        pass

    logger.info(
        f"Progress logged: user={message.author.id}, type={msg_type}, "
        f"topics={topics_str}, streak={streak['current_streak']}"
    )


def _classify_message(content: str) -> str:
    """Classify a message as 'plan', 'done', or 'progress'."""
    lower = content.lower()
    if lower.startswith("!plan"):
        return "plan"
    if lower.startswith("!done"):
        return "done"
    # Auto-detect
    plan_keywords = ["plan:", "planning to", "will study", "going to study", "today's plan"]
    done_keywords = ["done:", "completed", "finished", "solved", "practiced"]
    if any(kw in lower for kw in plan_keywords):
        return "plan"
    if any(kw in lower for kw in done_keywords):
        return "done"
    return "progress"
