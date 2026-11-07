# app/cache_manager.py
import time
import hashlib
from typing import Optional, Dict, Any

class ResponseCacheManager:
    """
    Provides in-memory response caching for frequent or repeated queries,
    supplying before/after evidence on cache hits versus cache misses.
    """
    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _normalize_key(cls, query: str) -> str:
        """Normalizes the query string to ensure cache hit consistency."""
        return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()

    @classmethod
    def get(cls, query: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached response if present."""
        key = cls._normalize_key(query)
        if key in cls._cache:
            entry = cls._cache[key]
            return {
                "hit": True,
                "cached_at": entry["timestamp"],
                "response": entry["response"]
            }
        return None

    @classmethod
    def set(cls, query: str, response: Dict[str, Any]) -> None:
        """Stores a response in the cache with timestamp."""
        key = cls._normalize_key(query)
        cls._cache[key] = {
            "timestamp": time.time(),
            "response": response
        }