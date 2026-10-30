"""Simple asynchronous/thread-safe in-memory TTL cache."""

import time
import logging
from typing import Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class SimpleTTLCache:
    """In-memory cache with Time-To-Live (TTL) expiration per key."""

    def __init__(self, default_ttl_seconds: int = 900):  # 15 minutes default
        self.default_ttl = default_ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value if key exists and has not expired."""
        if key not in self._store:
            return None
        expires_at, value = self._store[key]
        if time.time() > expires_at:
            # Expired
            del self._store[key]
            logger.debug(f"Cache key '{key}' expired and was removed.")
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store key-value pair with TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.time() + ttl
        self._store[key] = (expires_at, value)
        logger.debug(f"Cached key '{key}' with TTL {ttl}s.")

    def clear(self) -> None:
        """Clear all entries."""
        self._store.clear()


# Global cache instance for news fetchers
cache = SimpleTTLCache()

