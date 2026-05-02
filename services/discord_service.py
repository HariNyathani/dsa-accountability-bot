"""
Discord notification service — DMs and admin channel messages.
"""

import logging
import discord
from typing import Optional

logger = logging.getLogger("dsa_bot.discord_service")


async def send_dm(bot: discord.Client, user_id: int, message: str) -> bool:
    """Send a DM to the specified user. Returns True on success."""
    try:
        user = await bot.fetch_user(user_id)
        if user is None:
            logger.error(f"User {user_id} not found.")
            return False
        dm_channel = await user.create_dm()
        await dm_channel.send(message)
        logger.info(f"DM sent to {user_id}")
        return True
    except discord.Forbidden:
        logger.error(f"Cannot DM user {user_id} — DMs may be disabled.")
        return False
    except Exception as e:
        logger.error(f"Failed to DM user {user_id}: {e}")
        return False


async def send_to_channel(bot: discord.Client, channel_id: int, message: str) -> bool:
    """Send a message to a specific channel. Returns True on success."""
    if not channel_id:
        return False
    try:
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        if channel is None:
            logger.error(f"Channel {channel_id} not found.")
            return False
        await channel.send(message)
        logger.info(f"Message sent to channel {channel_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send to channel {channel_id}: {e}")
        return False


async def send_embed(
    bot: discord.Client,
    channel_id: int,
    embed: discord.Embed,
) -> bool:
    """Send an embed to a channel."""
    if not channel_id:
        return False
    try:
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        if channel is None:
            return False
        await channel.send(embed=embed)
        return True
    except Exception as e:
        logger.error(f"Failed to send embed to channel {channel_id}: {e}")
        return False


async def send_dm_embed(bot: discord.Client, user_id: int, embed: discord.Embed) -> bool:
    """Send an embed via DM."""
    try:
        user = await bot.fetch_user(user_id)
        dm_channel = await user.create_dm()
        await dm_channel.send(embed=embed)
        return True
    except Exception as e:
        logger.error(f"Failed to DM embed to {user_id}: {e}")
        return False
