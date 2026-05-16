"""
Legacy backward-compatibility shim.

All logic has been migrated to the `utils.resolvers` package.
This module re-exports `fuzzy_match_problem` and `invalidate_cache`
so any existing imports (Discord bot handlers, etc.) continue to work.

>>> from utils.matcher import fuzzy_match_problem   # still works
"""

from utils.resolvers import fuzzy_match_problem, invalidate_all_caches

# Re-export the old name
invalidate_cache = invalidate_all_caches
