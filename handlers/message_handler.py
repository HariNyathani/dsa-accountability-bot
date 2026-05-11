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
from utils.command_parser import parse_qdone, parse_plan_tomorrow
import json
import config

logger = logging.getLogger("dsa_bot.message_handler")


async def handle_message(message: discord.Message, bot: discord.Client):
    """
    Called for every message the bot sees.
    Checks if the author is a registered user tracking this channel.
    """
    # Ignore bots
    if message.author.bot:
        return

    content = message.content.strip()
    if not content:
        return

    # Admin Suite Commands
    if config.BOT_OWNER_ID and message.author.id == config.BOT_OWNER_ID:
        lower_content = content.lower()
        if lower_content.startswith("!qpurge"):
            if message.mentions:
                target_user = message.mentions[0]
                await database.delete_user_progress(target_user.id)
                await message.reply(f"⚠️ All data for {target_user.name} has been eradicated from the database.")
            return
        elif lower_content.startswith("!qundo"):
            if message.mentions:
                target_user = message.mentions[0]
                success = await database.undo_last_entry(target_user.id)
                if success:
                    await message.reply(f"✅ Reverted the latest entry for {target_user.name}.")
                else:
                    await message.reply(f"❌ No entries found for {target_user.name}.")
            return

    # Look up whether this user is registered AND tracking this channel
    user = await database.get_user_with_settings(message.author.id)
    if not user:
        return
    if not user.get("is_active"):
        return
    if user.get("tracked_channel_id") != message.channel.id:
        return



    # Ensure user has a consistent users table entry (safety net)
    await database.ensure_user(message.author.id, str(message.author))

    from services.progress_service import process_progress_submission
    result = await process_progress_submission(
        user_id=message.author.id,
        content=content,
        source="discord",
        channel_id=message.channel.id
    )

    if result.get("status") == "skipped":
        return
        
    if result.get("status") == "error":
        feedback = result.get("feedback_message")
        if feedback:
            try:
                await message.reply(feedback, delete_after=300)  # 5 min — user needs to read the error
            except discord.HTTPException:
                pass
        return

    msg_type = result["msg_type"]
    topics = result["topics"]
    parsed_fields_dict = result["parsed_fields"]
    streak = result["streak"]
    leetcode_matches = result.get("leetcode_matches", [])
    service_feedback = result.get("feedback_message", "")

    user_tz = user.get("timezone", "")
    today = today_str(user_tz)

    # React to confirm tracking
    feedback_msg = None
    try:
        import re
        has_url = bool(re.search(r'leetcode\.com/problems/', content.lower()))
        if content.lower().startswith("!qdone") or content.lower().startswith("!qn") or content.lower().startswith("!log") or has_url:
            await message.add_reaction("✅")
            
            # Unconditionally use the service's feedback and append running totals
            if parsed_fields_dict["log"]:
                user_logs = await database.get_progress_logs(message.author.id)
                topic_totals = {}
                for log in user_logs:
                    if log.get("topics"):
                        for t in log["topics"].split(", "):
                            t = t.strip()
                            if t:
                                topic_totals[t] = topic_totals.get(t, 0) + 1
                
                lines = [service_feedback] if service_feedback else []
                for item in parsed_fields_dict["log"]:
                    t = item["canonical_topic"]
                    total = topic_totals.get(t, 0)
                    lines.append(f"📊 {t.title()} Total: {total}")
                
                feedback_msg = "\n".join(lines)
            else:
                feedback_msg = "⚠️ Couldn't parse topics and counts. Use format: `!qdone arrays 5 recursion 2`"
        elif msg_type == "plan":
            await message.add_reaction("📋")
            feedback_msg = "📋 Plan logged for tomorrow."
        elif msg_type == "rest":
            await message.add_reaction("🛌")
            feedback_msg = service_feedback
        elif msg_type == "done":
            await message.add_reaction("✅")
            
            # If LeetCode match found, show the enhanced feedback
            if leetcode_matches and service_feedback:
                feedback_msg = service_feedback
            else:
                # Check for early completion of tomorrow's plan
                today_logs = await database.get_progress_logs(message.author.id, today, today)
                completed_early = []
                for t in topics:
                    for log in today_logs:
                        if log.get("parsed_fields"):
                            try:
                                pf = json.loads(log["parsed_fields"])
                                if pf.get("target_date") != today and pf.get("intent_type") == "plan":
                                    # planned for future
                                    for item in pf.get("log", []):
                                        if item.get("canonical_topic") == t:
                                            completed_early.append(t)
                            except:
                                pass
                if completed_early:
                    unique_early = list(set(completed_early))
                    feedback_msg = f"Nice, you completed tomorrow's planned task early: {', '.join(unique_early)}!"
                elif service_feedback and service_feedback != "Progress logged.":
                    feedback_msg = service_feedback
        else:
            # Free-text progress — reply with confirmation and react with fire
            if service_feedback and service_feedback != "Progress logged.":
                feedback_msg = service_feedback
            await message.add_reaction("🔥")
    except discord.HTTPException:
        pass

    if not feedback_msg:
        feedback_msg = "✅ Progress successfully logged."

    try:
        await message.reply(feedback_msg, delete_after=3600)  # 1 hour — keeps channel clean
    except:
        pass
