"""
LeetCode fuzzy matcher — matches user input against the local problem database.

Uses `rapidfuzz` for fast approximate string matching.
"""

import json
import logging
from typing import Optional, Tuple, List

import aiosqlite
from rapidfuzz import process, fuzz

import config
from utils.topic_extractor import TOPIC_PATTERNS

logger = logging.getLogger("dsa_bot.matcher")

def _map_and_dedup(tags_list: List[str]) -> List[str]:
    """Maps raw tags to canonical aliases and deduplicates them."""
    alias_map = {}
    for canonical, aliases in TOPIC_PATTERNS.items():
        for alias in aliases:
            alias_map[alias.lower()] = canonical

    seen = set()
    normalized = []
    for t in tags_list:
        t_lower = t.strip().lower()
        if not t_lower:
            continue
        
        if t_lower in alias_map:
            mapped = alias_map[t_lower].title()
        else:
            mapped = t.strip().title()
            
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

    db_path = config.DATABASE_PATH
    try:
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT question_id, title, title_slug, difficulty, topics FROM leetcode_problems"
            )
            rows = await cursor.fetchall()
            _problem_cache = [dict(r) for r in rows]
            logger.info(f"Loaded {len(_problem_cache)} LeetCode problems into matcher cache.")
            return _problem_cache
    except Exception as e:
        logger.warning(f"Could not load LeetCode problems for matching: {e}")
        return []


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
    # Remove "leetcode" prefix if present
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
