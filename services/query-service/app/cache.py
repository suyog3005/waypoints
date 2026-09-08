"""Redis cache-aside helper (architecture Section 6).

The Query Service checks Redis first; on a miss it reads the Read Store and
populates the cache. Redis is a cache, not the source of truth (Section 7), so
every operation here is *best-effort*: if Redis is unreachable we log and fall
through to the Read Store rather than failing the request.

Values are stored as JSON strings with a TTL. Keys are namespaced by endpoint
and query parameters so different filters never collide.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

import redis

logger = logging.getLogger(__name__)


class Cache:
    """Thin, best-effort wrapper over a Redis client."""

    def __init__(self, url: str, default_ttl: int = 60) -> None:
        self._default_ttl = default_ttl
        try:
            self._client: redis.Redis | None = redis.Redis.from_url(
                url, decode_responses=True
            )
            self._client.ping()
        except Exception as exc:  # noqa: BLE001 - best-effort: degrade to no-cache
            logger.warning("Redis unavailable at %s (%s); running without cache.", url, exc)
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Any | None:
        """Return the cached, JSON-decoded value, or None on miss/error."""
        if self._client is None:
            return None
        try:
            raw = self._client.get(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis GET %s failed: %s", key, exc)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            logger.warning("Cached value for %s was not valid JSON; ignoring.", key)
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a JSON-serialized value with a TTL. No-op if Redis is down."""
        if self._client is None:
            return
        try:
            self._client.set(key, json.dumps(value), ex=ttl or self._default_ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis SET %s failed: %s", key, exc)

    def invalidate_prefix(self, prefix: str) -> None:
        """Best-effort invalidation of all keys sharing a prefix (SCAN-based)."""
        if self._client is None:
            return
        try:
            for key in self._client.scan_iter(match=f"{prefix}*", count=200):
                self._client.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis invalidate_prefix %s failed: %s", prefix, exc)


def cache_key(endpoint: str, **params: Any) -> str:
    """Build a deterministic, collision-free cache key from an endpoint + params.

    Only non-None params are included, and they are sorted so the key is stable
    regardless of argument order.
    """
    parts = [endpoint]
    for k in sorted(params):
        if params[k] is not None:
            parts.append(f"{k}={params[k]}")
    return ":".join(parts)


def cache_get_or_load(
    cache: Cache,
    key: str,
    loader: Callable[[], Any],
    ttl: int | None = None,
) -> Any:
    """Cache-aside: return the cached value, else run ``loader``, cache, and return.

    ``loader`` is the Read Store query. The returned value is whatever the loader
    produced (already JSON-serializable, e.g. a list of dicts).
    """
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = loader()
    cache.set(key, value, ttl=ttl)
    return value
