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
    
    if web_topics is not None or content.lower().startswith("!qdone") or content.lower().startswith("!qn"):
        if web_topics is not None:
            qdone_results = [(t["canonical_topic"], t["question_count"], t.get("difficulty")) for t in web_topics]
        else:
            qdone_results = [(canonical, count, diff) for canonical, count, diff, raw in parse_qdone(content)]
            
        for canonical, count, diff in qdone_results:
            # Attempt fuzzy match against LeetCode database
            match = await fuzzy_match_problem(canonical)
            if match:
                # Use matched difficulty over user-provided difficulty if it exists
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
                # Store the canonical topic name as-is (count times) so that
                # comma-counting in get_message_count still equals the real
                # question count, NOT the number of tags.
                topics.extend([canonical] * count)
            else:
                log_entry = {
                    "canonical_topic": canonical,
                    "normalized_topic": canonical,
                    "question_count": count,
                    "leetcode_topics": canonical
                }
                if diff:
                    log_entry["leetcode_difficulty"] = diff.title()
                parsed_fields_dict["log"].append(log_entry)
                # To support legacy analytics without schema rewrite, repeat topic count times
                topics.extend([canonical] * count)
        msg_type = "done"
        parsed_fields_dict["intent_type"] = "done"
    else:
        # Standard extraction
        extracted = extract_topics(content)
        
        # If standard extraction found nothing, try fuzzy-matching the entire
        # message against LeetCode titles (user might have typed just a problem name)
        if not extracted:
            match = await fuzzy_match_problem(content)
            if match:
                leetcode_matches.append({
                    "original": content,
                    "matched_title": match["title"],
                    "difficulty": match["difficulty"],
                    "official_topics": match["topics_str"],
                    "score": match["score"],
                    "question_count": 1,
                })
                # Use the problem title as the single topic entry so
                # comma-counting = 1 question
                extracted = [match["title"]]
                parsed_fields_dict["log"].append({
                    "canonical_topic": match["title"],
                    "normalized_topic": match["title"],
                    "question_count": 1,
                    "leetcode_title": match["title"],
                    "leetcode_topics": match["topics_str"],
                    "leetcode_difficulty": match["difficulty"],
                })
        
        if not leetcode_matches:
            # No fuzzy match happened — try matching each extracted topic individually
            for t in extracted:
                match = await fuzzy_match_problem(t)
                if match:
                    leetcode_matches.append({
                        "original": t,
                        "matched_title": match["title"],
                        "difficulty": match["difficulty"],
                        "official_topics": match["topics_str"],
                        "score": match["score"],
                        "question_count": 1,
                    })
                    parsed_fields_dict["log"].append({
                        "canonical_topic": t,
                        "normalized_topic": t,
                        "question_count": 1,
                        "leetcode_title": match["title"],
                        "leetcode_topics": match["topics_str"],
                        "leetcode_difficulty": match["difficulty"],
                    })
                else:
                    parsed_fields_dict["log"].append({
                        "canonical_topic": t,
                        "normalized_topic": t,
                        "question_count": 1,
                        "leetcode_topics": t
                    })
        
        topics.extend(extracted)
        
        is_plan_tomorrow = parse_plan_tomorrow(content)
        if is_plan_tomorrow:
            # target date is tomorrow
            from utils.time_utils import parse_date
            from datetime import timedelta
            try:
                tomorrow_date = (parse_date(today) + timedelta(days=1)).strftime("%Y-%m-%d")
                parsed_fields_dict["target_date"] = tomorrow_date
            except Exception:
                pass
            parsed_fields_dict["intent_type"] = "plan"
            msg_type = "plan"

    topics_str = ", ".join(topics)
    parsed_fields_json = json.dumps(parsed_fields_dict)

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
