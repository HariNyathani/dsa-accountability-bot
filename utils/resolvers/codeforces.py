"""
Codeforces resolver — resolves CF problems by compound ID (e.g. "1189A"),
contest URL, or fuzzy title match against the local `codeforces_problems` table.

Difficulty banding:
  Easy:   rating <= 1199
  Medium: 1200 - 1599
  Hard:   1600 - 1999
  Expert: >= 2000
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

logger = logging.getLogger("dsa_bot.resolvers.codeforces")


def _map_and_dedup(tags_list: List[str]) -> List[str]:
    """Maps raw CF tags to canonical topic aliases and deduplicates."""
    seen = set()
    normalized = []
    for item in tags_list:
        if not item:
            continue
        for t in item.split(','):
            mapped = normalize_topic(t.strip())
            if mapped not in seen:
                seen.add(mapped)
                normalized.append(mapped)
    return normalized


def _normalize_cf_difficulty(rating: Optional[int]) -> str:
    """Map a Codeforces numerical rating to a normalized difficulty tier."""
    if rating is None:
        return "Unknown"
    if rating <= 1199:
        return "Easy"
    if rating <= 1599:
        return "Medium"
    if rating <= 1999:
        return "Hard"
    return "Expert"


# Regex to split a compound CF ID like "1189A" into (contest_id, index)
_CF_COMPOUND_RE = re.compile(r'^(\d+)\s*([A-Za-z]\d?)$')


class CodeforcesResolver(PlatformResolver):
    """Resolves Codeforces problems by compound ID, URL, or fuzzy title."""

    def __init__(self):
        self._cache: Optional[List[dict]] = None

    @property
    def platform_name(self) -> str:
        return "codeforces"

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
                            "SELECT contest_id, problem_index, title, rating, tags FROM codeforces_problems"
                        )
                        rows = cur.fetchall()
                        parsed = []
                        for r in rows:
                            d = dict(r)
                            if isinstance(d.get("tags"), (list, dict)):
                                d["tags"] = json.dumps(d["tags"])
                            parsed.append(d)
                        return parsed
            except Exception as e:
                logger.warning(f"Could not load Codeforces problems: {e}")
                return []

        self._cache = await asyncio.to_thread(_sync)
        if self._cache:
            logger.info(f"Loaded {len(self._cache)} Codeforces problems into resolver cache.")
        return self._cache

    def _build_result(self, problem: dict, score: float = 100.0) -> ResolvedProblem:
        """Build a ResolvedProblem from a raw CF DB row."""
        try:
            tag_list = json.loads(problem.get("tags") or "[]")
        except (json.JSONDecodeError, TypeError):
            tag_list = []
        tag_list = _map_and_dedup(tag_list)

        contest_id = problem["contest_id"]
        index = problem["problem_index"]
        compound_id = f"{contest_id}{index}"
        title = problem.get("title", "")
        rating = problem.get("rating")

        return ResolvedProblem(
            platform="codeforces",
            problem_id=compound_id,
            title=title,
            difficulty_raw=str(rating) if rating else "Unrated",
            difficulty_norm=_normalize_cf_difficulty(rating),
            topics=tag_list,
            topics_str=", ".join(tag_list),
            url=f"https://codeforces.com/contest/{contest_id}/problem/{index}",
            score=score,
            extra={"cf_rating": rating, "contest_id": contest_id, "problem_index": index},
        )

    async def resolve(self, identifier: str, threshold: int = 70) -> Optional[ResolvedProblem]:
        """
        Resolve a Codeforces problem from:
          - Compound ID: "1189A", "1189 A"
          - Full URL: codeforces.com/contest/1189/problem/A
                      codeforces.com/problemset/problem/1189/A
          - Fuzzy title match
        """
        problems = await self._load_problems()
        if not problems:
            return None

        cleaned = identifier.strip()

        # 1. Check for CF URL
        url_match = re.search(
            r'codeforces\.com/(?:contest/(\d+)/problem/([A-Za-z]\d?)|problemset/problem/(\d+)/([A-Za-z]\d?))',
            cleaned
        )
        if url_match:
            cid = int(url_match.group(1) or url_match.group(3))
            idx = (url_match.group(2) or url_match.group(4)).upper()
            for p in problems:
                if p["contest_id"] == cid and p["problem_index"].upper() == idx:
                    return self._build_result(p, score=100.0)
            return None  # Strict URL but not found

        # 2. Compound ID: "1189A" or "1189 A"
        compound_match = _CF_COMPOUND_RE.match(cleaned)
        if compound_match:
            cid, idx = int(compound_match.group(1)), compound_match.group(2).upper()
            for p in problems:
                if p["contest_id"] == cid and p["problem_index"].upper() == idx:
                    return self._build_result(p, score=100.0)
            return None  # Looked like a CF ID but not found

        # 3. Strip "codeforces" or "cf" prefix for fuzzy matching
        for prefix in ("codeforces", "cf", "cf-", "cf "):
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip(" -#.")
                break

        if not cleaned:
            return None

        # 4. Fuzzy title match
        title_map = {p.get("title", ""): p for p in problems if p.get("title")}
        titles = list(title_map.keys())
        if not titles:
            return None

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
