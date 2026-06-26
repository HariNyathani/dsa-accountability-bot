"""
Per-route TTL cache for read-only FastAPI endpoints.

Wraps an async route function with a :class:`cachetools.TTLCache` so identical
requests within the TTL window are served from memory. The cache key is the
function name plus the resolved argument tuple (FastAPI passes primitives —
``int`` / ``str`` / ``Optional[str]`` — so args are naturally hashable).

NOTE: each process / worker maintains its own cache instance. The current
deployment target is a single-process single-worker FastAPI app, so this is
acceptable. Once we move to multi-worker (e.g. gunicorn -w N) the cache will
be N independent snapshots — agents will add a shared cache layer for that.
"""

import logging
from functools import wraps

from cachetools import TTLCache

logger = logging.getLogger("dsa_bot.api.cache")

DEFAULT_MAXSIZE = 128
DEFAULT_TTL = 60


def cached_route(ttl: int = DEFAULT_TTL, maxsize: int = DEFAULT_MAXSIZE):
    """Decorator that memoises an async FastAPI route for ``ttl`` seconds."""
    def decorator(func):
        cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            cached = cache.get(key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            cache[key] = result
            return result

        wrapper.__cache__ = cache  # type: ignore[attr-defined]
        return wrapper

    return decorator
