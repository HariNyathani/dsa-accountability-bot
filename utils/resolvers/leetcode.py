"""
LeetCode resolver — migrated from the original utils/matcher.py.

Resolves LeetCode problem identifiers (numeric IDs, URL slugs, fuzzy titles)
against the local `leetcode_problems` database table.
"""

import json
import logging
import re
import asyncio
from typing import Optional, List

import psycopg2
import psycopg2.extras
from rapidfuzz import process, fuzz

from db.database import db_manager
from utils.topic_extractor import normalize_topic
from utils.resolvers.base import PlatformResolver, ResolvedProblem

logger = logging.getLogger("dsa_bot.resolvers.leetcode")


def _map_and_dedup(tags_list: List[str]) -> List[str]:
    """Maps raw tags to canonical aliases and deduplicates them."""
    seen = set()
    normalized = []
    for item in tags_list:
        if not item:
            continue
        for t in item.split(','):
            mapped = normalize_topic(t)
            if mapped not in seen:
                seen.add(mapped)
                normalized.append(mapped)
    return normalized


class LeetCodeResolver(PlatformResolver):
    """Resolves LeetCode problems by ID, slug, URL, or fuzzy title match."""

    def __init__(self):
        self._cache: Optional[List[dict]] = None

    @property
    def platform_name(self) -> str:
        return "leetcode"

    def invalidate_cache(self) -> None:
        self._cache = None

    async def _load_problems(self) -> List[dict]:
        if self._cache is not None:
            return self._cache

        def _sync():
            try:
                with db_manager.get_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                        cur.execute(
                            "SELECT question_id, title, title_slug, difficulty, topics FROM leetcode_problems"
                        )
                        rows = cur.fetchall()
                        parsed_rows = []
                        for r in rows:
                            d = dict(r)
                            if isinstance(d.get("topics"), (list, dict)):
                                d["topics"] = json.dumps(d["topics"])
                            parsed_rows.append(d)
                        return parsed_rows
            except Exception as e:
                logger.warning(f"Could not load LeetCode problems for matching: {e}")
                return []

        self._cache = await asyncio.to_thread(_sync)
        if self._cache:
            logger.info(f"Loaded {len(self._cache)} LeetCode problems into resolver cache.")
        return self._cache

    def _build_result(self, problem: dict, score: float = 100.0) -> ResolvedProblem:
        """Build a ResolvedProblem from a raw DB row."""
        try:
            topic_list = json.loads(problem.get("topics") or "[]")
        except (json.JSONDecodeError, TypeError):
            topic_list = []
        topic_list = _map_and_dedup(topic_list)

        qid = problem["question_id"]
        title = problem["title"]
        difficulty = problem.get("difficulty", "")
        slug = problem.get("title_slug", "")

        return ResolvedProblem(
            platform="leetcode",
            problem_id=str(qid),
            title=title,
            difficulty_raw=difficulty,
            difficulty_norm=difficulty if difficulty in ("Easy", "Medium", "Hard") else "Unknown",
            topics=topic_list,
            topics_str=", ".join(topic_list),
            url=f"https://leetcode.com/problems/{slug}/" if slug else "",
            score=score,
        )

    async def resolve(self, identifier: str, threshold: int = 70) -> Optional[ResolvedProblem]:
        """
        Resolve a LeetCode problem from various input formats:
          - Full URL: leetcode.com/problems/two-sum
          - Slug: two-sum
          - Numeric ID: 1, #1
          - Fuzzy title: "two sum", "twosum"
        """
        problems = await self._load_problems()
        if not problems:
            return None

        title_map = {p["title"]: p for p in problems}
        titles = list(title_map.keys())
        if not titles:
            return None

        cleaned = identifier.strip()

        # 1. Check for LeetCode URL
        slug_match = re.search(r'leetcode\.com/problems/([^/>\s]+)', cleaned)
        target_slug = slug_match.group(1) if slug_match else None

        # 2. Or maybe the user passed the exact slug (no spaces)
        if not target_slug and " " not in cleaned:
            target_slug = cleaned.lower()

        if target_slug:
            for p in problems:
                if p.get("title_slug") == target_slug:
                    return self._build_result(p, score=100.0)
            if slug_match:
                return None  # Was a strict URL but not found

        # Strip common prefixes for fuzzy matching
        for prefix in ("leetcode", "lc", "lc-", "lc "):
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip(" -#.")
                break

        if not cleaned:
            return None

        # Exact ID match
        possible_id = cleaned.lstrip("#")
        if possible_id.isdigit():
            target_id = int(possible_id)
            for p in problems:
                if p["question_id"] == target_id:
                    return self._build_result(p, score=100.0)

        # Fuzzy title match
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
        return self._build_result(problem, score=score)
