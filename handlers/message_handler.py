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
from utils.command_parser import parse_qdone
from ui.confidence_view import ConfidenceView
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

    logger.info(
        f"[GATE:ENTRY] user={message.author.id} channel={message.channel.id} "
        f"content={content[:80]!r}"
    )

    # Admin Suite Commands
    if config.BOT_OWNER_ID and message.author.id == config.BOT_OWNER_ID:
        lower_content = content.lower()
        if lower_content.startswith("!qpurge"):
            if message.mentions:
                target_user = message.mentions[0]
                await database.delete_user_progress(target_user.id)
                await message.reply(f"⚠️ All data for {target_user.name} has been eradicated from the database.", delete_after=3600)
            return
        elif lower_content.startswith("!qundo"):
            if message.mentions:
                target_user = message.mentions[0]
                success = await database.undo_last_entry(target_user.id)
                if success:
                    await message.reply(f"✅ Reverted the latest entry for {target_user.name}.", delete_after=3600)
                else:
                    await message.reply(f"❌ No entries found for {target_user.name}.", delete_after=3600)
            return

    # Look up whether this user is registered AND tracking this channel
    user = await database.get_user_with_settings(message.author.id)
    if not user:
        logger.debug(f"[GATE:NOT_REGISTERED] user={message.author.id} — ignoring")
        return
    if not user.get("is_active"):
        logger.debug(f"[GATE:INACTIVE] user={message.author.id} — ignoring")
        return
    if user.get("tracked_channel_id") != message.channel.id:
        logger.debug(
            f"[GATE:WRONG_CHANNEL] user={message.author.id} "
            f"tracked={user.get('tracked_channel_id')} actual={message.channel.id}"
        )
        return

    logger.info(f"[GATE:PASS] user={message.author.id} — routing to progress_service")



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
        logger.info(f"[GATE:RESULT_SKIPPED] user={message.author.id} — progress_service returned 'skipped'")
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
        has_url = bool(re.search(r'(?:leetcode\.com/problems/|codeforces\.com/(?:contest/\d+/problem/|problemset/problem/\d+/))', content.lower()))
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

        elif msg_type == "rest":
            await message.add_reaction("🛌")
            feedback_msg = service_feedback
        elif msg_type == "done":
            await message.add_reaction("✅")
            
            # Show enhanced feedback from service
            if service_feedback and service_feedback != "Progress logged.":
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

    # ── SRS Confidence Prompt ─────────────────────────────────────────────────
    # Send one dropdown prompt per resolved LeetCode problem that has a
    # numeric question_id.  Batch logs (!qdone 73, 75) get separate replies
    # so each problem gets an independent confidence score.
    srs_candidates = [
        m for m in result.get("leetcode_matches", [])
        if m.get("question_id") and str(m["question_id"]).isdigit()
    ]

    for match in srs_candidates:
        problem_id = int(match["question_id"])
        title      = match.get("matched_title") or match.get("original", "this problem")
        difficulty = match.get("difficulty", "")
        diff_badge = f" [{difficulty}]" if difficulty else ""

        prompt_text = (
            f"⭐ **How confident do you feel about: {title}{diff_badge}?**\n"
            f"-# Select a rating below — auto-saves as 🟡 Okay in 60 s."
        )

        view = ConfidenceView(
            author_id=message.author.id,
            problem_id=problem_id,
            user_id=message.author.id,
        )
        try:
            conf_msg = await message.reply(prompt_text, view=view)
            view.message = conf_msg   # required so on_timeout can edit the message
        except discord.HTTPException as exc:
            logger.warning(f"[SRS] Could not send confidence prompt: {exc}")
