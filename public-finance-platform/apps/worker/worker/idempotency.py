from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import redis

from worker.config import settings

logger = logging.getLogger("public_finance.worker.idempotency")


def stable_job_key(task_name: str, params: dict[str, Any]) -> str:
    serialized = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
    digest = sha256(f"{task_name}|{serialized}".encode("utf-8")).hexdigest()
    return f"{task_name}:{digest}"


@dataclass(frozen=True, slots=True)
class IdempotencyDecision:
    should_run: bool
    key: str
    reason: str


class RedisIdempotencyStore:
    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or settings.celery_broker_url

    def acquire(self, key: str, *, force: bool = False) -> IdempotencyDecision:
        if force:
            return IdempotencyDecision(should_run=True, key=key, reason="forced")
        try:
            client = redis.Redis.from_url(self.redis_url, socket_connect_timeout=1, socket_timeout=1)
            acquired = client.set(
                f"idempotency:{key}",
                "running",
                nx=True,
                ex=settings.idempotency_lock_ttl_seconds,
            )
            if acquired:
                return IdempotencyDecision(should_run=True, key=key, reason="acquired")
            return IdempotencyDecision(should_run=False, key=key, reason="already_running_or_completed")
        except redis.RedisError as exc:
            logger.warning("idempotency_store_unavailable; running fail-open: %s", exc)
            return IdempotencyDecision(should_run=True, key=key, reason="store_unavailable_fail_open")

    def mark_complete(self, key: str) -> None:
        try:
            client = redis.Redis.from_url(self.redis_url, socket_connect_timeout=1, socket_timeout=1)
            client.set(
                f"idempotency:{key}",
                "completed",
                ex=settings.idempotency_lock_ttl_seconds,
            )
        except redis.RedisError as exc:
            logger.warning("idempotency_mark_complete_failed: %s", exc)


idempotency_store = RedisIdempotencyStore()
