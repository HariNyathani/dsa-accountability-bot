import logging
import json
import re
from db import database
from utils.time_utils import today_str, now_iso
from utils.topic_extractor import extract_topics
from utils.streak_utils import on_post
from utils.command_parser import parse_qdone
from utils.resolvers import resolve_problem, fuzzy_match_problem
from utils.resolvers.detector import detect_platform

logger = logging.getLogger("dsa_bot.progress_service")


# ── Multiline / Bullet-List Parser ──────────────────────────────────────────

_BULLET_RE = re.compile(r'^\s*[-*•]\s+(.+)', re.MULTILINE)

# Platform names that are "noise" — they appear as headers but carry no
# topic meaning.  Stripped from headers; if a header becomes empty after
# stripping, its bullets are merged into the previous group.
_PLATFORM_NOISE = {
    "cses", "atcoder", "leetcode", "codeforces", "codechef",
    "striver", "neetcode", "hackerrank", "hackerearth", "gfg",
    "geeksforgeeks", "interviewbit", "spoj",
}


def _strip_platform_noise(header: str) -> str:
    """Remove platform-name words from a header string.

    'CSES Graph' → 'Graph',  'Atcoder' → '',  'Striver DP' → 'DP'
    """
    words = header.split()
    cleaned = [w for w in words if w.lower() not in _PLATFORM_NOISE]
    return " ".join(cleaned).strip()


def _parse_bullet_list(content: str) -> list[dict] | None:
    """
    Detect a "Topic Header + bullet items" pattern.

    Examples it should match:
        CSES Graph
         - Problem A
         - Problem B

        Graphs:
         • BFS basics
         • Dijkstra

    Platform-noise headers (e.g. 'Atcoder', 'CSES') are transparent:
    their bullets are merged into the preceding group.

    Returns a list of dicts with keys: header, items
    Returns None if no bullet-list structure is detected.
    """
    lines = content.strip().splitlines()
    if len(lines) < 2:
        return None

    # Find bullet lines
    bullet_indices = [i for i, line in enumerate(lines) if _BULLET_RE.match(line)]
    if not bullet_indices:
        return None

    # Group bullets under their nearest preceding non-bullet header.
    # Pure-noise headers (platform names with no topic) are skipped so
    # their bullets stay attached to the last real header.
    groups = []
    current_header = None
    current_items = []

    for i, line in enumerate(lines):
        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            if current_header is None:
                # Bullets without a header — use empty context
                current_header = ""
            current_items.append(bullet_match.group(1).strip())
        else:
            # Non-bullet line — potential header
            raw_header = line.strip().rstrip(':').strip()
            if not raw_header:
                continue

            cleaned_header = _strip_platform_noise(raw_header)

            if not cleaned_header:
                # Pure platform noise (e.g. "Atcoder") — DON'T start
                # a new group.  Subsequent bullets stay with current_header.
                logger.info(f"[GATE:BULLET_NOISE] Skipping platform-noise header: '{raw_header}'")
                continue

            # Real header — flush previous group and start new one
            if current_header is not None and current_items:
                groups.append({"header": current_header, "items": current_items})
            current_header = cleaned_header
            current_items = []

    # Flush last group
    if current_header is not None and current_items:
        groups.append({"header": current_header, "items": current_items})

    if not groups:
        return None

    logger.info(f"[GATE:BULLET_PARSE] Detected {len(groups)} bullet group(s): {groups}")
    return groups


# ── Natural-Language LeetCode Fallback ──────────────────────────────────────

_ACTION_VERBS_RE = re.compile(
    r'\b(solved|done|completed|finished|practiced|attempted|revised|reviewed|did)\b',
    re.IGNORECASE
)


def _strip_action_verbs(text: str) -> str:
    """Strip common action-verb prefixes so 'solved Two Sum' becomes 'Two Sum'."""
    return _ACTION_VERBS_RE.sub('', text).strip(' ,.-:')


async def _try_leetcode_fallback(content: str) -> list[dict]:
    """
    Attempt to fuzzy-match the entire message (or sub-lines) against the
    LeetCode database.  Returns a list of match dicts (same shape as
    fuzzy_match_problem output), or an empty list.
    """
    matches = []

    # Strategy 1: Try the whole message (minus action verbs) as one query
    candidate = _strip_action_verbs(content).strip()
    # Remove LeetCode URLs (already handled upstream)
    candidate = re.sub(r'https?://\S+', '', candidate).strip()

    if candidate:
        match = await fuzzy_match_problem(candidate, threshold=75)
        if match:
            logger.info(
                f"[GATE:LC_FALLBACK] Whole-message match: '{candidate}' → "
                f"'{match['title']}' (score={match['score']:.1f})"
            )
            matches.append(match)
            return matches

    # Strategy 2: Try each non-blank line individually
    seen_titles = set()
    for line in content.strip().splitlines():
        line_candidate = _strip_action_verbs(line).strip()
        if len(line_candidate) < 3:
            continue
        match = await fuzzy_match_problem(line_candidate, threshold=78)
        if match and match["title"] not in seen_titles:
            logger.info(
                f"[GATE:LC_FALLBACK] Line match: '{line_candidate}' → "
                f"'{match['title']}' (score={match['score']:.1f})"
            )
            seen_titles.add(match["title"])
            matches.append(match)

    return matches


# ── Helpers: convert ResolvedProblem → legacy dict shapes ───────────────────

def _resolved_to_match_dict(resolved) -> dict:
    """Convert a ResolvedProblem dataclass into the dict shape used by
    leetcode_matches[] and the feedback builder."""
    return {
        "original": resolved.title,
        "matched_title": resolved.title,
        "difficulty": resolved.difficulty_norm,
        "official_topics": resolved.topics_str,
        "score": resolved.score,
        "question_count": 1,
        "platform": resolved.platform,
        "question_id": int(resolved.problem_id) if resolved.problem_id and resolved.problem_id.isdigit() else None,
    }


def _resolved_to_log_entry(resolved, count: int = 1) -> dict:
    """Convert a ResolvedProblem into a log-entry dict for parsed_fields."""
    return {
        "canonical_topic": resolved.title,
        "normalized_topic": resolved.title,
        "question_count": count,
        "leetcode_title": resolved.title,
        "leetcode_topics": resolved.topics_str,
        "leetcode_difficulty": resolved.difficulty_norm,
        "platform": resolved.platform,
    }


# ── URL regexes (platform-agnostic) ────────────────────────────────────────

_PROBLEM_URL_RE = re.compile(
    r'(?:leetcode\.com/problems/([^/>\s]+)'
    r'|codeforces\.com/(?:contest/(\d+)/problem/([A-Za-z]\d?)|problemset/problem/(\d+)/([A-Za-z]\d?)))',
    re.IGNORECASE,
)


# ── SRS Confidence Interval Schedule ────────────────────────────────────────
#
# Maps a self-reported confidence score (1-5) to the number of days until the
# problem should resurface in the revision queue.
#   1 = Blackout  -> review again tomorrow
#   2 = Hard      -> 2 days
#   3 = Okay      -> 5 days
#   4 = Easy      -> 10 days
#   5 = Confident -> 30 days

CONFIDENCE_INTERVAL_DAYS = {1: 1, 2: 2, 3: 5, 4: 10, 5: 30}


# ── Main Entry Point ────────────────────────────────────────────────────────

async def process_progress_submission(
    user_id: int,
    content: str,
    source: str = "discord",
    channel_id: int = 0,
    override_date: str = None,
    web_topics: list = None,
    acting_user_id: int = None,
    confidence: int | None = None,
    is_review: bool = False,
) -> dict:
    """
    Canonical backend progress-recording service.
    Used by both Discord message handler and Web dashboard.

    Parameters
    ----------
    confidence : int | None
        Self-reported confidence score 1-5 (used for SRS scheduling).
        Only meaningful for LeetCode problems.  Ignored for other platforms.
    is_review : bool
        When True, this submission is a spaced-repetition review session rather
        than a first-time solve.  Review sessions are logged with
        ``is_review=True`` in progress_logs and trigger a revision_bank UPSERT,
        but they do NOT update the streak or daily_status (to avoid inflating
        the user's first-time-solve metrics).
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
    logger.info(f"[GATE:CLASSIFY] user={user_id} msg_type='{msg_type}' content={content[:80]!r}")

    # Parsing logic
    parsed_fields_dict = {
        "intent_type": msg_type,
        "target_date": today,
        "log": [],
        "source": source,
        "platform": "leetcode",  # default; overridden by platform-aware callers
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

    # ── Platform-agnostic URL / !log handling ────────────────────────────
    url_match = _PROBLEM_URL_RE.search(content)
    is_log_command = content_lower.startswith("!log ")

    if msg_type != "rest" and (is_log_command or url_match):
        logger.info(f"[GATE:URL_OR_LOG] user={user_id} is_log={is_log_command} has_url={bool(url_match)}")

        if url_match:
            # Single URL — resolve as before
            targets = [url_match.group(0)]
            is_bare_ids = False
        else:
            raw_arg = content[5:].strip()  # strip "!log "
            # Detect a bare numeric-list input (e.g. "1,2" or "1 2" or "1, 2").
            # If the string contains ONLY digits, commas, and spaces it is treated
            # as a list of LeetCode IDs.  Otherwise fall back to the original
            # single-identifier resolve (URL slug, Codeforces ID, title).
            import re as _re
            if _re.fullmatch(r'[\d,\s]+', raw_arg):
                # Aggressive extraction: pull every contiguous digit sequence
                extracted = _re.findall(r'\d+', raw_arg)
                targets = [f"#{n}" for n in extracted]  # prepend '#' → numeric ID path
                is_bare_ids = True
            else:
                targets = [raw_arg]
                is_bare_ids = False

        first_error: str | None = None
        for target in targets:
            original_display = target
            resolved = await resolve_problem(target)

            if not resolved:
                if is_log_command and not is_bare_ids:
                    # Single-identifier mode — return hard error immediately
                    return {
                        "status": "error",
                        "feedback_message": "❌ Invalid ID/URL or problem not found."
                    }
                elif is_log_command and is_bare_ids:
                    # Multi-ID mode — collect first error, continue other IDs
                    if first_error is None:
                        first_error = target.lstrip('#')
                    logger.warning(f"[GATE:LOG_BATCH] ID {target!r} not found — skipping")
                    continue
                else:
                    return {"status": "skipped"}

            msg_type = "done"
            parsed_fields_dict["intent_type"] = "done"
            parsed_fields_dict["platform"] = resolved.platform

            match_dict = _resolved_to_match_dict(resolved)
            match_dict["original"] = original_display
            match_dict["question_count"] = 1
            leetcode_matches.append(match_dict)

            parsed_fields_dict["log"].append(_resolved_to_log_entry(resolved))
            topics.append(resolved.title)

        # If every ID in a batch failed, surface an error
        if is_log_command and is_bare_ids and not topics and not parsed_fields_dict["log"]:
            return {
                "status": "error",
                "feedback_message": "❌ None of the provided IDs could be found. Check the numbers and try again."
            }
        
    elif web_topics is not None or content_lower.startswith("!qdone") or content_lower.startswith("!qn"):
        logger.info(f"[GATE:QDONE_QN] user={user_id} web_topics={web_topics is not None}")
        is_qn = content_lower.startswith("!qn")
        if web_topics is not None:
            qdone_results = [(t["canonical_topic"], t["question_count"], t.get("difficulty")) for t in web_topics]
        elif is_qn:
            # Aggressive extraction: pull every contiguous digit sequence from
            # the argument string so "187,188, 189 190" → ['187','188','189','190'].
            # Non-digit tokens (Codeforces IDs like "4A", "2211B") are also kept
            # so CF support is not broken: re.findall(r'\d+', ...) would strip the
            # letter suffix, so we split on commas/spaces and strip each token instead.
            import re as _re
            raw_qn_arg = content[4:].strip()  # strip "!qn "
            # If the whole arg is purely numeric separators, extract digit runs.
            # Otherwise split on comma/whitespace to preserve mixed tokens (e.g. "4A").
            if _re.fullmatch(r'[\d,\s]+', raw_qn_arg):
                tokens = _re.findall(r'\d+', raw_qn_arg)
            else:
                tokens = [t.strip() for t in _re.split(r'[,\s]+', raw_qn_arg) if t.strip()]
            qdone_results = [(tok, 1, None) for tok in tokens]
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
                # Use platform-agnostic resolve_problem instead of
                # LeetCode-only fuzzy_match_problem.
                # detect_platform will route "2211B" → codeforces,
                # "#1" or "1" → leetcode (via fallback).
                identifier = canonical
                # If the identifier is purely numeric, prepend '#' so the
                # LeetCode resolver treats it as an ID lookup (preserves
                # backward compat with existing `!qn 1` behaviour).
                if identifier.isdigit():
                    identifier = f"#{identifier}"

                resolved = await resolve_problem(identifier)
                match = None
                if resolved:
                    match = _resolved_to_match_dict(resolved)
                    match["original"] = canonical
                    match["question_count"] = count
                    parsed_fields_dict["platform"] = resolved.platform
            else:
                match = None
                resolved = None

            if is_qn and not match:
                return {
                    "status": "error",
                    "feedback_message": f"❌ Problem '{canonical}' not found. Check the ID/URL and try again."
                }

            if match and resolved:
                final_diff = resolved.difficulty_norm or diff
                match["difficulty"] = final_diff
                leetcode_matches.append(match)
                log_entry = _resolved_to_log_entry(resolved, count)
                log_entry["leetcode_difficulty"] = final_diff
                parsed_fields_dict["log"].append(log_entry)
                # Use resolved.title (e.g. "Watermelon") instead of raw
                # canonical (e.g. "4A") so topics_str saved to DB matches
                # the canonical_topic in parsed_fields — this is what the
                # message_handler's "Total:" counter looks up against.
                topics.extend([resolved.title] * count)
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
        logger.info(f"[GATE:FREETEXT] user={user_id} Entering free-text extraction pipeline")

        # ── STAGE 1: Bullet-list parsing (checked FIRST) ────────────────
        # If the message has a "header + bullets" structure, each bullet
        # counts as 1 question.  This MUST run before keyword extraction
        # because keyword extraction on the full text would find the
        # header keyword and report count=1, ignoring the bullet items.
        bullet_groups = _parse_bullet_list(content)
        if bullet_groups:
            logger.info(f"[GATE:BULLET_LIST] user={user_id} Detected bullet list, processing items")
            # Sticky topic: if a group's header has no recognizable topic,
            # inherit the last known canonical topic so platform-noise
            # headers like "Atcoder" don't orphan their bullets.
            last_known_canonical = None

            for group in bullet_groups:
                header = group["header"]
                # Try to get a canonical topic from the header (e.g. "Graph" → "Graphs")
                header_topics = extract_topics(header)
                header_canonical = header_topics[0][0] if header_topics else None

                if header_canonical:
                    last_known_canonical = header_canonical
                    logger.info(f"[GATE:BULLET_TOPIC_SET] New sticky topic: '{header_canonical}' (from header '{header}')")
                else:
                    # Inherit last known topic
                    header_canonical = last_known_canonical
                    logger.info(f"[GATE:BULLET_TOPIC_INHERIT] Header '{header}' has no topic, inheriting '{last_known_canonical}'")

                for item_text in group["items"]:
                    # Try LeetCode match on each bullet item
                    item_match = await fuzzy_match_problem(item_text, threshold=75)
                    if item_match:
                        logger.info(
                            f"[GATE:BULLET_LC] Bullet '{item_text}' → "
                            f"'{item_match['title']}' (score={item_match['score']:.1f})"
                        )
                        leetcode_matches.append({
                            "original": item_match["title"],
                            "matched_title": item_match["title"],
                            "difficulty": item_match["difficulty"],
                            "official_topics": item_match["topics_str"],
                            "score": item_match["score"],
                            "question_count": 1,
                            "question_id": item_match["question_id"],
                        })
                        parsed_fields_dict["log"].append({
                            "canonical_topic": item_match["title"],
                            "normalized_topic": item_match["title"],
                            "question_count": 1,
                            "leetcode_title": item_match["title"],
                            "leetcode_topics": item_match["topics_str"],
                            "leetcode_difficulty": item_match["difficulty"],
                        })
                        topics.append(item_match["title"])
                    elif header_canonical:
                        # No LC match, but we have a topic (own or inherited)
                        logger.info(
                            f"[GATE:BULLET_TOPIC] Bullet '{item_text}' logged under topic '{header_canonical}'"
                        )
                        parsed_fields_dict["log"].append({
                            "canonical_topic": header_canonical,
                            "normalized_topic": header_canonical,
                            "question_count": 1,
                            "leetcode_topics": header_canonical
                        })
                        topics.append(header_canonical)

            if topics:
                msg_type = "done"
                parsed_fields_dict["intent_type"] = "done"

        # ── STAGE 2: Line-by-line Fuzzy-First pipeline ──────────────────
        # For each line: try the LeetCode fuzzy matcher FIRST.
        # Only fall back to keyword extraction if the fuzzy matcher finds
        # nothing for that specific line.  This prevents generic keywords
        # that appear as substrings inside a problem title (e.g. "tree"
        # inside "Binary Tree Zigzag Level Order Traversal") from
        # intercepting specific LeetCode problems.
        if not bullet_groups:
            logger.info(f"[GATE:LINE_ITER] user={user_id} Starting line-by-line fuzzy-first pipeline")
            seen_lc_titles: set[str] = set()

            for raw_line in content.strip().splitlines():
                line = _strip_action_verbs(raw_line).strip()
                # Drop bare URLs — already handled upstream
                line = re.sub(r'https?://\S+', '', line).strip()
                if len(line) < 3:
                    continue

                # ── Priority 1: LeetCode fuzzy match ────────────────────
                lc_line_matches = await _try_leetcode_fallback(line)
                if lc_line_matches:
                    for match in lc_line_matches:
                        if match["title"] in seen_lc_titles:
                            continue
                        seen_lc_titles.add(match["title"])
                        logger.info(
                            f"[GATE:LINE_LC_HIT] '{line}' → "
                            f"'{match['title']}' (score={match['score']:.1f})"
                        )
                        # IMPORTANT: "original" MUST equal match["title"] so
                        # _build_feedback can de-duplicate against topics[].
                        leetcode_matches.append({
                            "original": match["title"],
                            "matched_title": match["title"],
                            "difficulty": match["difficulty"],
                            "official_topics": match["topics_str"],
                            "score": match["score"],
                            "question_count": 1,
                            "question_id": match["question_id"],
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

                else:
                    # ── Priority 2: Keyword extraction on this line only ─
                    line_topics = extract_topics(line)
                    if line_topics:
                        logger.info(
                            f"[GATE:LINE_KEYWORD_HIT] '{line}' → keywords: {line_topics}"
                        )
                        for canon, count in line_topics:
                            parsed_fields_dict["log"].append({
                                "canonical_topic": canon,
                                "normalized_topic": canon,
                                "question_count": count,
                                "leetcode_topics": canon,
                            })
                            topics.extend([canon] * count)
                    else:
                        logger.info(f"[GATE:LINE_MISS] No match for line: '{line}'")

            # Use parsed_fields_dict["log"] as the authoritative signal:
            # topics[] mirrors it for backward compat, but LC matches that
            # skip the topics list (e.g. future refactors) must still trigger
            # "done".  Checking the log directly is the safe invariant.
            if topics or parsed_fields_dict["log"]:
                msg_type = "done"
                parsed_fields_dict["intent_type"] = "done"
                logger.info(
                    f"[GATE:LINE_ITER_HIT] user={user_id} "
                    f"Pipeline resolved {len(parsed_fields_dict['log'])} log entry/entries"
                )
            else:
                logger.info(
                    f"[GATE:LINE_ITER_MISS] user={user_id} "
                    f"Line-by-line pipeline found nothing"
                )



    # Silence the Noise: Abort if nothing was extracted.
    # Guard on the log, not just topics[], so LC-only sessions
    # (which populate parsed_fields_dict["log"] directly) are never silently dropped.
    if not topics and not parsed_fields_dict["log"]:
        logger.info(f"[GATE:SKIP] user={user_id} No topics or log entries found — skipping")
        return {
            "status": "skipped"
        }

    topics_str = ", ".join(topics)

    # ── Audit trail: record admin override before serialization ──────
    if acting_user_id is not None:
        parsed_fields_dict["admin_override_by"] = acting_user_id

    parsed_fields_json = json.dumps(parsed_fields_dict)

    # Rate Limits
    new_quantity = sum(item.get("question_count", 0) for item in parsed_fields_dict.get("log", []))
    
    if new_quantity > 25:
        return {
            "status": "error",
            "feedback_message": "❌ Limit exceeded. You can only log up to 25 questions per command to keep data realistic."
        }
        
    if new_quantity > 0:
        current_sum = await database.get_daily_question_count(user_id, today)
        if (current_sum + new_quantity) > 25:
            return {
                "status": "error",
                "feedback_message": "❌ Daily limit reached (25/day). Quality over quantity, legend! See you tomorrow."
            }

    # Save progress log
    log_platform = parsed_fields_dict.get("platform", "leetcode")
    await database.save_progress_log(
        user_id=user_id,
        channel_id=channel_id,
        message_content=content,
        topics=topics_str,
        posted_at=now,
        log_date=today,
        message_type=msg_type,
        parsed_fields=parsed_fields_json,
        platform=log_platform,
        is_review=is_review,
    )

    # ── Streak & daily_status: ONLY update for first-time solves ──────
    # Review sessions must NOT count toward the daily posting streak —
    # only original problem solves should advance the streak counter.
    if not is_review:
        await database.mark_posted(user_id, today)
        streak = await on_post(user_id, today)
    else:
        # For review sessions, return the current streak without modifying it
        streak = await database.get_streak(user_id)

    logger.info(
        f"Progress logged: user={user_id}, source={source}, type={msg_type}, "
        f"topics={topics_str}, streak={streak.get('current_streak', 0)}, "
        f"is_review={is_review}"
    )

    # ── Revision Bank UPSERT (SRS scheduling) ─────────────────────────
    # Triggered when:
    #   - platform is 'leetcode' (revision_bank references leetcode_problems)
    #   - a valid confidence score (1-5) was provided
    #   - the log contains at least one resolved LeetCode problem with a question_id
    if log_platform == "leetcode" and confidence is not None and 1 <= confidence <= 5:
        from datetime import datetime, timezone, timedelta
        interval_days = CONFIDENCE_INTERVAL_DAYS[confidence]
        next_review_at = (
            datetime.now(timezone.utc) + timedelta(days=interval_days)
        ).isoformat()

        # Find the resolved LeetCode question_id from leetcode_matches or parsed_fields
        problem_id: int | None = None
        for entry in parsed_fields_dict.get("log", []):
            # The resolver stores the numeric question_id in the platform log entry;
            # we dig it out from leetcode_matches which carries the resolved object.
            pass

        # Fall back: look in leetcode_matches for a numeric problem_id
        # (populated via resolve_problem which returns question_id as problem_id attr)
        for match in leetcode_matches:
            qid = match.get("question_id") or match.get("problem_id")
            if qid and str(qid).isdigit():
                problem_id = int(qid)
                break

        if problem_id:
            try:
                await database.upsert_revision_bank(
                    user_id=user_id,
                    problem_id=problem_id,
                    confidence=confidence,
                    next_review_at=next_review_at,
                )
                logger.info(
                    f"[SRS] Upserted revision_bank: user={user_id}, "
                    f"problem_id={problem_id}, confidence={confidence}, "
                    f"next_review_at={next_review_at}"
                )
            except Exception as srs_err:
                # Non-fatal: SRS failure must not break the main log flow
                logger.warning(f"[SRS] upsert_revision_bank failed: {srs_err}")

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
    If LeetCode/Codeforces matches were found, include the canonical title and auto-tagged topics.
    Append any non-matched manual topics.
    """
    if not topics and not leetcode_matches:
        return "Progress logged."

    lines = []
    matched_originals = set()
    
    # Process LeetCode-enhanced feedback
    for m in leetcode_matches:
        matched_originals.add(m.get("original"))
        matched_originals.add(m.get("matched_title"))
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
    """Classify a message as 'done', 'rest', or 'progress'."""
    lower = content.lower()
    if lower.startswith("!rest") or lower.startswith("!cheatday"):
        return "rest"
    if lower.startswith("!done"):
        return "done"
    # Auto-detect
    done_keywords = ["done:", "completed", "finished", "solved", "practiced"]
    if any(kw in lower for kw in done_keywords):
        return "done"
    return "progress"
