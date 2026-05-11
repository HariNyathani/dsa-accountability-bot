import logging
import json
from db import database
from utils.time_utils import today_str, now_iso
from utils.topic_extractor import extract_topics
from utils.streak_utils import on_post
from utils.command_parser import parse_qdone, parse_plan_tomorrow
from utils.matcher import fuzzy_match_problem

logger = logging.getLogger("dsa_bot.progress_service")

async def process_progress_submission(
    user_id: int,
    content: str,
    source: str = "discord",
    channel_id: int = 0,
    override_date: str = None,
    web_topics: list = None
) -> dict:
    """
    Canonical backend progress-recording service.
    Used by both Discord message handler and Web dashboard.
    """
    # Ensure user exists
    user = await database.get_user(user_id)
    if not user:
        await database.ensure_user(user_id)
        user = await database.get_user(user_id)

    user_tz = user.get("timezone", "")
    today = override_date if override_date else today_str(user_tz)
    now = now_iso(user_tz)

    # Removed anti-duplicate check to allow independent logs of the same topic

    # Determine message type
    msg_type = _classify_message(content)

    # Parsing logic
    parsed_fields_dict = {
        "intent_type": msg_type,
        "target_date": today,
        "log": [],
        "source": source
    }
    
    topics = []
    leetcode_matches = []  # Track successful fuzzy matches for feedback
    
    content_lower = content.lower()
    
    if msg_type == "rest":
        if await database.has_rest_today(user_id, today):
            return {
                "status": "error",
                "feedback_message": "❌ You've already used a Rest Day for today! One is enough—go relax or solve a quick problem. 🛌"
            }
            
        current_month = today[:7]
        rest_count = await database.get_monthly_rest_count(user_id, current_month)
        if rest_count >= 4:
            return {
                "status": "error",
                "feedback_message": "❌ You've used all 4 Rest Days for this month. Even a 5-minute Arrays session counts! Push through. ⚔️"
            }
        parsed_fields_dict["log"].append({
            "canonical_topic": "Rest",
            "normalized_topic": "Rest",
            "question_count": 0,
            "leetcode_difficulty": "None"
        })
        topics.append("Rest")

    import re
    url_match = re.search(r'leetcode\.com/problems/([^/>\s]+)', content_lower)
    is_log_command = content_lower.startswith("!log ")
    
    if msg_type != "rest" and (is_log_command or url_match):
        if url_match:
            target = url_match.group(1)
            original_display = url_match.group(0)
        else:
            target = content_lower.replace("!log ", "", 1).strip()
            original_display = target
            
        match = await fuzzy_match_problem(target)
        if not match:
            if is_log_command:
                return {
                    "status": "error",
                    "feedback_message": "❌ Invalid LeetCode URL or problem not found."
                }
            else:
                return {
                    "status": "skipped"
                }
            
        msg_type = "done"
        parsed_fields_dict["intent_type"] = "done"
        leetcode_matches.append({
            "original": original_display,
            "matched_title": match["title"],
            "difficulty": match["difficulty"],
            "official_topics": match["topics_str"],
            "score": match["score"],
            "question_count": 1,
        })
        parsed_fields_dict["log"].append({
            "canonical_topic": match["title"],
            "normalized_topic": match["title"],
            "question_count": 1,
            "leetcode_title": match["title"],
            "leetcode_topics": match["topics_str"],
            "leetcode_difficulty": match["difficulty"],
        })
        topics.append(match["title"])
        
    elif web_topics is not None or content_lower.startswith("!qdone") or content_lower.startswith("!qn"):
        is_qn = content_lower.startswith("!qn")
        if web_topics is not None:
            qdone_results = [(t["canonical_topic"], t["question_count"], t.get("difficulty")) for t in web_topics]
        elif is_qn:
            target_id = content[4:].strip()
            qdone_results = [(target_id, 1, None)]
        else:
            try:
                qdone_results = [(canonical, count, diff) for canonical, count, diff, raw in parse_qdone(content)]
            except ValueError as e:
                return {
                    "status": "error",
                    "feedback_message": f"❌ {str(e)}"
                }
            
        for canonical, count, diff in qdone_results:
            if is_qn:
                match = await fuzzy_match_problem(f"#{canonical}")
            else:
                match = None
                
            if is_qn and not match:
                return {
                    "status": "error",
                    "feedback_message": f"❌ Question ID {canonical} not found in our database. Try logging with the URL instead."
                }
                
            if match:
                final_diff = match.get("difficulty", diff)
                leetcode_matches.append({
                    "original": canonical,
                    "matched_title": match["title"],
                    "difficulty": final_diff,
                    "official_topics": match["topics_str"],
                    "score": match["score"],
                    "question_count": count,
                })
                parsed_fields_dict["log"].append({
                    "canonical_topic": canonical,
                    "normalized_topic": canonical,
                    "question_count": count,
                    "leetcode_title": match["title"],
                    "leetcode_topics": match["topics_str"],
                    "leetcode_difficulty": final_diff,
                })
                topics.extend([canonical] * count)
            else:
                from utils.command_parser import get_canonical_topic
                if not get_canonical_topic(canonical):
                    canonical = "Uncategorized"
                
                log_entry = {
                    "canonical_topic": canonical,
                    "normalized_topic": canonical,
                    "question_count": count,
                    "leetcode_topics": canonical
                }
                if diff:
                    log_entry["leetcode_difficulty"] = diff.title()
                parsed_fields_dict["log"].append(log_entry)
                topics.extend([canonical] * count)
        msg_type = "done"
        parsed_fields_dict["intent_type"] = "done"
    elif msg_type != "rest":
        # Standard extraction without fuzzy matching
        extracted = extract_topics(content)
        
        for canon, count in extracted:
            parsed_fields_dict["log"].append({
                "canonical_topic": canon,
                "normalized_topic": canon,
                "question_count": count,
                "leetcode_topics": canon
            })
            topics.extend([canon] * count)
        
        is_plan_tomorrow = parse_plan_tomorrow(content)
        if is_plan_tomorrow:
            from utils.time_utils import parse_date
            from datetime import timedelta
            try:
                tomorrow_date = (parse_date(today) + timedelta(days=1)).strftime("%Y-%m-%d")
                parsed_fields_dict["target_date"] = tomorrow_date
            except Exception:
                pass
            parsed_fields_dict["intent_type"] = "plan"
            msg_type = "plan"

    # Silence the Noise: Abort if nothing was extracted and it's not a plan
    if msg_type != "plan" and not topics:
        return {
            "status": "skipped"
        }

    topics_str = ", ".join(topics)
    parsed_fields_json = json.dumps(parsed_fields_dict)

    # Rate Limits
    new_quantity = sum(item.get("question_count", 0) for item in parsed_fields_dict.get("log", []))
    
    if new_quantity > 10:
        return {
            "status": "error",
            "feedback_message": "❌ Limit exceeded. You can only log up to 10 questions per command to keep data realistic."
        }
        
    if msg_type != "plan" and new_quantity > 0:
        current_sum = await database.get_daily_question_count(user_id, today)
        if (current_sum + new_quantity) > 25:
            return {
                "status": "error",
                "feedback_message": "❌ Daily limit reached (25/day). Quality over quantity, legend! See you tomorrow."
            }

    # Save progress log
    await database.save_progress_log(
        user_id=user_id,
        channel_id=channel_id,
        message_content=content,
        topics=topics_str,
        posted_at=now,
        log_date=today,
        message_type=msg_type,
        parsed_fields=parsed_fields_json,
    )

    # Mark today as posted
    if msg_type != "plan":
        await database.mark_posted(user_id, today)

    # Update streak
    if msg_type != "plan":
        streak = await on_post(user_id, today)
    else:
        streak = await database.get_streak(user_id)

    logger.info(
        f"Progress logged: user={user_id}, source={source}, type={msg_type}, "
        f"topics={topics_str}, streak={streak.get('current_streak', 0)}"
    )

    # Build feedback message
    if msg_type == "rest":
        current_month = today[:7]
        rest_count = await database.get_monthly_rest_count(user_id, current_month)
        feedback_message = f"🛌 **Rest Day Logged.** (Used {rest_count}/4 this month). Your {streak.get('current_streak', 0)} day streak is preserved. Recharging is part of the grind-see you tomorrow! 🌙"
    else:
        feedback_message = _build_feedback(topics, leetcode_matches, msg_type)

    return {
        "status": "success",
        "msg_type": msg_type,
        "topics": topics,
        "parsed_fields": parsed_fields_dict,
        "streak": streak,
        "leetcode_matches": leetcode_matches,
        "feedback_message": feedback_message,
    }


def _build_feedback(topics: list, leetcode_matches: list, msg_type: str) -> str:
    """
    Build a human-friendly feedback string.
    If LeetCode matches were found, include the canonical title and auto-tagged topics.
    Append any non-LeetCode manual topics.
    """
    if not topics and not leetcode_matches:
        return "Progress logged."

    lines = []
    matched_originals = set()
    
    # Process LeetCode-enhanced feedback
    for m in leetcode_matches:
        matched_originals.add(m.get("original"))
        count = m.get("question_count", 1)
        title = m["matched_title"]
        difficulty = m.get("difficulty", "")
        official = m.get("official_topics", "")

        difficulty_badge = ""
        if difficulty:
            difficulty_badge = f" [{difficulty}]"

        if official:
            lines.append(
                f"✅ Logged {count} question{'s' if count != 1 else ''}: "
                f"{title}{difficulty_badge} (Auto-tagged: {official})"
            )
        else:
            lines.append(
                f"✅ Logged {count} question{'s' if count != 1 else ''}: "
                f"{title}{difficulty_badge}"
            )

    # Process remaining (manual) topics
    manual_topics = [t for t in topics if t not in matched_originals]
    if manual_topics:
        from collections import Counter
        counts = Counter(manual_topics)
        for topic, count in counts.items():
            lines.append(f"✅ Logged {count} question{'s' if count != 1 else ''}: {topic.title()}")

    if not lines:
        return "Progress logged."

    return "\n".join(lines)


def _classify_message(content: str) -> str:
    """Classify a message as 'plan', 'done', or 'progress'."""
    lower = content.lower()
    if lower.startswith("!plan"):
        return "plan"
    if lower.startswith("!rest") or lower.startswith("!cheatday"):
        return "rest"
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
