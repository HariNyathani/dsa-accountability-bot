"""
Platform auto-detector — examines a user-supplied identifier and determines
which platform it belongs to before dispatching to a specific resolver.

Detection priority:
  1. URL domain match  (leetcode.com, codeforces.com)
  2. Structural pattern (CF compound ID like "1189A")
  3. Default fallback   (leetcode — preserves existing behaviour)
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger("dsa_bot.resolvers.detector")

# ── URL patterns ────────────────────────────────────────────────────────────

_LEETCODE_URL_RE = re.compile(r'leetcode\.com/problems/([^/>\s]+)', re.IGNORECASE)

_CODEFORCES_URL_RE = re.compile(
    r'codeforces\.com/(?:contest/(\d+)/problem/([A-Za-z]\d?)|problemset/problem/(\d+)/([A-Za-z]\d?))',
    re.IGNORECASE
)

# ── Non-URL structural patterns ─────────────────────────────────────────────

# Codeforces compound IDs: "1189A", "4A", "1189B2"
_CF_COMPOUND_RE = re.compile(r'^\d+\s*[A-Za-z]\d?$')


def detect_platform(identifier: str) -> Tuple[str, str]:
    """
    Detect the platform from a raw user identifier.

    Parameters
    ----------
    identifier : str
        Raw user input — could be a URL, compound ID, numeric ID, or title.

    Returns
    -------
    tuple[str, str]
        (platform_name, cleaned_identifier)

    Detection rules (priority order):
      1. LeetCode URL    → ("leetcode", slug)
      2. Codeforces URL  → ("codeforces", "1189A")
      3. CF compound ID  → ("codeforces", "1189A")
      4. Fallback        → ("leetcode", original)  [preserves existing behaviour]
    """
    raw = identifier.strip()

    # ── 1. URL-based detection ───────────────────────────────────────────

    lc_match = _LEETCODE_URL_RE.search(raw)
    if lc_match:
        logger.debug(f"[DETECT] LeetCode URL detected: {raw}")
        return ("leetcode", raw)  # Pass the full input; LC resolver handles it

    cf_match = _CODEFORCES_URL_RE.search(raw)
    if cf_match:
        cid = cf_match.group(1) or cf_match.group(3)
        idx = cf_match.group(2) or cf_match.group(4)
        compound = f"{cid}{idx.upper()}"
        logger.debug(f"[DETECT] Codeforces URL detected: {raw} → {compound}")
        return ("codeforces", raw)  # Pass full input; CF resolver handles URL parsing

    # ── 2. Structural pattern detection ──────────────────────────────────

    # CF compound ID (e.g. "1189A", "4A", "1189B2")
    if _CF_COMPOUND_RE.match(raw):
        logger.debug(f"[DETECT] Codeforces compound ID detected: {raw}")
        return ("codeforces", raw)

    # ── 3. Fallback: assume LeetCode (preserves existing behaviour) ──────
    logger.debug(f"[DETECT] No platform signal found, defaulting to leetcode: {raw}")
    return ("leetcode", raw)
