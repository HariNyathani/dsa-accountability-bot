"""
LeetCode fuzzy matcher — matches user input against the local problem database.

Uses `rapidfuzz` for fast approximate string matching.
"""

import json
import logging
from typing import Optional, Tuple, List
import asyncio

import psycopg2
import psycopg2.extras
from rapidfuzz import process, fuzz

import config
from db.database import db_manager
from utils.topic_extractor import TOPIC_PATTERNS

logger = logging.getLogger("dsa_bot.matcher")

from utils.topic_extractor import normalize_topic

def _map_and_dedup(tags_list: List[str]) -> List[str]:
    """Maps raw tags to canonical aliases and deduplicates them."""
    seen = set()
    normalized = []
    
    for item in tags_list:
        if not item:
            continue
        # Split by comma in case a single string contains multiple tags
        for t in item.split(','):
            mapped = normalize_topic(t)
            if mapped not in seen:
                seen.add(mapped)
                normalized.append(mapped)
    return normalized


# Cache to avoid re-querying SQLite on every single log
_problem_cache: Optional[List[dict]] = None


async def _load_problems() -> List[dict]:
    """Load all problem titles + topics from the local database (cached)."""
    global _problem_cache
    if _problem_cache is not None:
        return _problem_cache

    def _sync():
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(
                        "SELECT question_id, title, title_slug, difficulty, topics FROM leetcode_problems"
                    )
                    rows = cur.fetchall()
                    # Convert dict elements, handle JSONB topics if returned as dict/list natively
                    parsed_rows = []
                    for r in rows:
                        d = dict(r)
                        if isinstance(d.get("topics"), list) or isinstance(d.get("topics"), dict):
                            d["topics"] = json.dumps(d["topics"])
                        parsed_rows.append(d)
                    return parsed_rows
        except Exception as e:
            logger.warning(f"Could not load LeetCode problems for matching: {e}")
            return []

    _problem_cache = await asyncio.to_thread(_sync)
    if _problem_cache:
        logger.info(f"Loaded {len(_problem_cache)} LeetCode problems into matcher cache.")
    return _problem_cache


def invalidate_cache():
    """Clear the in-memory problem cache (e.g. after a re-sync)."""
    global _problem_cache
    _problem_cache = None


async def fuzzy_match_problem(raw_input: str, threshold: int = 70) -> Optional[dict]:
    """
    Attempt to fuzzy-match the user's input against LeetCode problem titles.

    Parameters
    ----------
    raw_input : str
        The raw topic/problem text the user typed (e.g. "twosum", "two sum",
        "3sum", "longest palindromic substring").
    threshold : int
        Minimum score (0-100) to accept a match. Default 70.

    Returns
    -------
    dict or None
        On match:  {"question_id": int, "title": str, "difficulty": str,
                    "topics": list[str], "topics_str": str, "score": float}
        On miss:   None
    """
    problems = await _load_problems()
    if not problems:
        return None

    # Build a mapping of title -> problem dict for quick lookup
    title_map = {p["title"]: p for p in problems}
    titles = list(title_map.keys())

    if not titles:
        return None

    # Clean input: strip common prefixes users might type
    cleaned = raw_input.strip()
    
    import re
    # 1. Check if the raw input contains a LeetCode URL
    slug_match = re.search(r'leetcode\.com/problems/([^/>\s]+)', cleaned)
    target_slug = slug_match.group(1) if slug_match else None
    
    # 2. Or maybe the user just passed the exact slug
    if not target_slug and not " " in cleaned:
        target_slug = cleaned.lower()
        
    if target_slug:
        for p in problems:
            if p.get("title_slug") == target_slug:
                try:
                    topic_list = json.loads(p.get("topics") or "[]")
                except (json.JSONDecodeError, TypeError):
                    topic_list = []
                topic_list = _map_and_dedup(topic_list)
                return {
                    "question_id": p["question_id"],
                    "title": p["title"],
                    "difficulty": p.get("difficulty", ""),
                    "topics": topic_list,
                    "topics_str": ", ".join(topic_list),
                    "score": 100.0,
                }
        if slug_match:
            return None # If it was a strict URL but not found, fail immediately

    # Remove "leetcode" prefix if present for fuzzy matching
    for prefix in ("leetcode", "lc", "lc-", "lc "):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip(" -#.")
            break

    if not cleaned:
        return None

    # Exact ID Match Support
    possible_id = cleaned.lstrip("#")
    if possible_id.isdigit():
        target_id = int(possible_id)
        for p in problems:
            if p["question_id"] == target_id:
                try:
                    topic_list = json.loads(p.get("topics") or "[]")
                except (json.JSONDecodeError, TypeError):
                    topic_list = []
                
                topic_list = _map_and_dedup(topic_list)
                
                return {
                    "question_id": p["question_id"],
                    "title": p["title"],
                    "difficulty": p.get("difficulty", ""),
                    "topics": topic_list,
                    "topics_str": ", ".join(topic_list),
                    "score": 100.0,
                }

    # Use token_set_ratio for flexibility with word order and partial matches
    result = process.extractOne(
        cleaned,
        titles,
        scorer=fuzz.token_set_ratio,
        score_cutoff=threshold,
    )

    if result is None:
        return None

    matched_title, score, _idx = result
    problem = title_map[matched_title]

    # Parse the JSON topics array
    try:
        topic_list = json.loads(problem.get("topics") or "[]")
    except (json.JSONDecodeError, TypeError):
        topic_list = []

    topic_list = _map_and_dedup(topic_list)
    topics_str = ", ".join(topic_list)

    return {
        "question_id": problem["question_id"],
        "title": problem["title"],
        "difficulty": problem.get("difficulty", ""),
        "topics": topic_list,
        "topics_str": topics_str,
        "score": score,
    }
