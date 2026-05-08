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

    # Parsing logic
    parsed_fields_dict = {
        "intent_type": msg_type,
        "target_date": today,
        "log": []
    }
    
    topics = []
    
    if content.lower().startswith("!qdone"):
        qdone_results = parse_qdone(content)
        for canonical, count, raw in qdone_results:
            parsed_fields_dict["log"].append({
                "canonical_topic": canonical,
                "normalized_topic": canonical,
                "question_count": count
            })
            # To support legacy analytics without schema rewrite, repeat topic count times
            topics.extend([canonical] * count)
        msg_type = "done"
        parsed_fields_dict["intent_type"] = "done"
    else:
        # Standard extraction
        extracted = extract_topics(content)
        topics.extend(extracted)
        
        is_plan_tomorrow = parse_plan_tomorrow(content)
        if is_plan_tomorrow:
            # target date is tomorrow
            from utils.time_utils import parse_date
            from datetime import timedelta
            tomorrow_date = (parse_date(today) + timedelta(days=1)).strftime("%Y-%m-%d")
            parsed_fields_dict["target_date"] = tomorrow_date
            parsed_fields_dict["intent_type"] = "plan"
            msg_type = "plan"
            
        for t in extracted:
            parsed_fields_dict["log"].append({
                "canonical_topic": t,
                "normalized_topic": t,
                "question_count": 1
            })

    topics_str = ", ".join(topics)
    parsed_fields_json = json.dumps(parsed_fields_dict)

    # Ensure user has a consistent users table entry (safety net)
    await database.ensure_user(message.author.id, str(message.author))

    # Save progress log
    await database.save_progress_log(
        user_id=message.author.id,
        channel_id=message.channel.id,
        message_content=content,
        topics=topics_str,
        posted_at=now,
        log_date=today,
        message_type=msg_type,
        parsed_fields=parsed_fields_json,
    )

    # Mark today as posted
    await database.mark_posted(message.author.id, today)

    # Update streak
    streak = await on_post(message.author.id, today)

    # React to confirm tracking
    feedback_msg = None
    try:
        if content.lower().startswith("!qdone"):
            await message.add_reaction("✅")
            
            # Rich feedback response
            if parsed_fields_dict["log"]:
                lines = []
                # Fetch total counts for these topics from DB to show rich stats
                user_logs = await database.get_progress_logs(message.author.id)
                topic_totals = {}
                for log in user_logs:
                    if log.get("topics"):
                        for t in log["topics"].split(", "):
                            t = t.strip()
                            if t:
                                topic_totals[t] = topic_totals.get(t, 0) + 1
                                
                for item in parsed_fields_dict["log"]:
                    t = item["canonical_topic"]
                    c = item["question_count"]
                    total = topic_totals.get(t, 0)
                    lines.append(f"✅ Logged {c} {t.title()} questions.\n📊 {t.title()} Total: {total}")
                
                feedback_msg = "\n\n".join(lines)
            else:
                feedback_msg = "⚠️ Couldn't parse topics and counts. Use format: `!qdone arrays 5 recursion 2`"
        elif msg_type == "plan":
            await message.add_reaction("📋")
        elif msg_type == "done":
            await message.add_reaction("✅")
            
            # Check for early completion of tomorrow's plan
            # Look at yesterday's logs to see if they planned this for today (which was "tomorrow" then)
            # Actually, "planned recursion for tomorrow but completes it today" -> planned it TODAY for tomorrow, but completed it TODAY.
            # So look at today's logs for a "plan_tomorrow" containing this topic.
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
        else:
            await message.add_reaction("🔥")
    except discord.HTTPException:
        pass

    if feedback_msg:
        try:
            await message.reply(feedback_msg)
        except:
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
