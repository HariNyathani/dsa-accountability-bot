"""
Platform resolver registry.

Provides a unified API surface:
  - RESOLVERS: dict of platform → PlatformResolver instance
  - resolve_problem(): auto-detect platform and resolve in one call
  - fuzzy_match_problem(): backward-compatible shim for existing code
"""

import logging
from typing import Optional, Dict

from utils.resolvers.base import PlatformResolver, ResolvedProblem
from utils.resolvers.leetcode import LeetCodeResolver
from utils.resolvers.codeforces import CodeforcesResolver
from utils.resolvers.detector import detect_platform

logger = logging.getLogger("dsa_bot.resolvers")

# ── Resolver instances ──────────────────────────────────────────────────────

RESOLVERS: Dict[str, PlatformResolver] = {
    "leetcode": LeetCodeResolver(),
    "codeforces": CodeforcesResolver(),
}


# ── Convenience functions ───────────────────────────────────────────────────

async def resolve_problem(
    identifier: str,
    platform: Optional[str] = None,
    threshold: int = 70,
) -> Optional[ResolvedProblem]:
    """
    Resolve a problem identifier, optionally auto-detecting the platform.

    Parameters
    ----------
    identifier : str
        The raw user input (URL, ID, title, etc.)
    platform : str or None
        If provided, use this platform's resolver directly.
        If None, auto-detect the platform from the identifier.
    threshold : int
        Fuzzy match score cutoff (0-100).

    Returns
    -------
    ResolvedProblem or None
    """
    if platform is None:
        platform, cleaned = detect_platform(identifier)
    else:
        platform = platform.lower().strip()
        cleaned = identifier

    resolver = RESOLVERS.get(platform)
    if resolver is None:
        logger.warning(f"No resolver registered for platform '{platform}'")
        return None

    return await resolver.resolve(cleaned, threshold=threshold)


async def fuzzy_match_problem(raw_input: str, threshold: int = 70) -> Optional[dict]:
    """
    Backward-compatible wrapper that returns the old dict format.

    This allows all existing code that calls fuzzy_match_problem()
    to continue working without changes during the migration period.
    """
    # Force LeetCode resolver for backward compat
    resolved = await RESOLVERS["leetcode"].resolve(raw_input, threshold=threshold)
    if resolved is None:
        return None

    return {
        "question_id": int(resolved.problem_id),
        "title": resolved.title,
        "difficulty": resolved.difficulty_raw,
        "topics": resolved.topics,
        "topics_str": resolved.topics_str,
        "score": resolved.score,
    }


def invalidate_all_caches() -> None:
    """Clear caches for all registered resolvers."""
    for resolver in RESOLVERS.values():
        resolver.invalidate_cache()
