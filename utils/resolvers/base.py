"""
Resolved problem dataclass and abstract PlatformResolver interface.

All platform resolvers return a ResolvedProblem so the rest of the system
never needs to know which platform a problem came from.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ResolvedProblem:
    """Unified output shape for all platform resolvers."""
    platform: str               # "leetcode" | "codeforces"
    problem_id: str             # platform-native ID  (LC: "1", CF: "1189A")
    title: str
    difficulty_raw: str         # native difficulty ("Easy", "1400")
    difficulty_norm: str        # normalized ("Easy" | "Medium" | "Hard" | "Expert" | "Unknown")
    topics: List[str]           # canonical topics after normalize_topic()
    topics_str: str             # comma-joined topics string
    url: str                    # canonical problem URL
    score: float = 100.0        # match confidence (0-100)
    extra: dict = field(default_factory=dict)  # platform-specific metadata (e.g. cf_rating)


class PlatformResolver(abc.ABC):
    """Abstract interface that all platform resolvers must implement."""

    @property
    @abc.abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g. 'leetcode', 'codeforces')."""
        ...

    @abc.abstractmethod
    async def resolve(self, identifier: str, threshold: int = 70) -> Optional[ResolvedProblem]:
        """
        Resolve a user-supplied identifier (ID, URL slug, title, etc.)
        to a ResolvedProblem, or return None if not found.
        """
        ...

    @abc.abstractmethod
    def invalidate_cache(self) -> None:
        """Clear any in-memory caches (e.g. after a data re-sync)."""
        ...
