from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any


@dataclass(slots=True)
class _CacheEntry:
    expires_at: datetime
    payload: Any


class InMemoryTTLCache:
    """Simple process-local TTL cache for read-heavy API endpoints."""

    def __init__(self, default_ttl_seconds: int = 60) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._store: dict[str, _CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        now = datetime.now(UTC)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._store.pop(key, None)
                return None
            return entry.payload

    def set(self, key: str, payload: Any, ttl_seconds: int | None = None) -> None:
        now = datetime.now(UTC)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        with self._lock:
            self._store[key] = _CacheEntry(expires_at=now + timedelta(seconds=ttl), payload=payload)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


read_cache = InMemoryTTLCache(default_ttl_seconds=90)
