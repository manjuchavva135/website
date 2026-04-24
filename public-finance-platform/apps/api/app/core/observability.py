from __future__ import annotations

import contextvars
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

CORRELATION_ID_HEADER = "X-Correlation-ID"
correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id",
    default=None,
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None) or correlation_id_var.get(),
        }
        for key in (
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
            "event",
            "error",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


@dataclass
class MetricsRegistry:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latency_ms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    lock: Lock = field(default_factory=Lock)

    def increment(self, name: str, labels: dict[str, str] | None = None, value: int = 1) -> None:
        key = self._key(name, labels)
        with self.lock:
            self.counters[key] += value

    def observe_latency(self, name: str, duration_ms: float, labels: dict[str, str] | None = None) -> None:
        key = self._key(name, labels)
        with self.lock:
            values = self.latency_ms[key]
            values.append(duration_ms)
            if len(values) > 1000:
                del values[: len(values) - 1000]

    def render_prometheus(self) -> str:
        lines: list[str] = [
            "# HELP http_requests_total Total HTTP requests handled by the API.",
            "# TYPE http_requests_total counter",
        ]
        with self.lock:
            for key, value in sorted(self.counters.items()):
                lines.append(f"{key} {value}")
            lines.extend(
                [
                    "# HELP http_request_duration_ms_avg Rolling average request duration in milliseconds.",
                    "# TYPE http_request_duration_ms_avg gauge",
                ]
            )
            for key, values in sorted(self.latency_ms.items()):
                avg = sum(values) / len(values) if values else 0
                metric = key.replace("http_request_duration_ms", "http_request_duration_ms_avg", 1)
                lines.append(f"{metric} {avg:.3f}")
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self.lock:
            self.counters.clear()
            self.latency_ms.clear()

    def _key(self, name: str, labels: dict[str, str] | None) -> str:
        if not labels:
            return name
        label_text = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
        return f"{name}{{{label_text}}}"


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self.requests: dict[str, deque[float]] = defaultdict(deque)
        self.lock = Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        if limit <= 0:
            return True, limit
        now = time.monotonic()
        with self.lock:
            bucket = self.requests[key]
            while bucket and now - bucket[0] >= window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                return False, 0
            bucket.append(now)
            return True, max(limit - len(bucket), 0)

    def reset(self) -> None:
        with self.lock:
            self.requests.clear()


metrics_registry = MetricsRegistry()
rate_limiter = FixedWindowRateLimiter()
logger = logging.getLogger("public_finance.api")


def get_correlation_id() -> str:
    return correlation_id_var.get() or ""


def is_public_api_path(path: str) -> bool:
    if not path.startswith("/api/v1/"):
        return False
    excluded_prefixes = ("/api/v1/admin", "/api/v1/health", "/api/v1/ops")
    return not path.startswith(excluded_prefixes)


def install_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid4())
        token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        route_family = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        try:
            if settings.public_api_rate_limit_enabled and is_public_api_path(request.url.path):
                allowed, remaining = rate_limiter.allow(
                    f"{client_ip}:{request.url.path}",
                    limit=settings.public_api_rate_limit_per_minute,
                )
                if not allowed:
                    metrics_registry.increment(
                        "http_requests_total",
                        {"path": route_family, "method": request.method, "status": "429"},
                    )
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"},
                        headers={
                            CORRELATION_ID_HEADER: correlation_id,
                            "X-RateLimit-Remaining": "0",
                            "Retry-After": "60",
                        },
                    )
            else:
                remaining = settings.public_api_rate_limit_per_minute

            response = await call_next(request)
            duration_ms = (time.perf_counter() - started) * 1000
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            if is_public_api_path(request.url.path):
                response.headers["X-RateLimit-Remaining"] = str(remaining)
            metrics_registry.increment(
                "http_requests_total",
                {"path": route_family, "method": request.method, "status": str(response.status_code)},
            )
            metrics_registry.observe_latency(
                "http_request_duration_ms",
                duration_ms,
                {"path": route_family, "method": request.method},
            )
            logger.info(
                "request_completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 3),
                    "client_ip": client_ip,
                    "event": "http_request",
                },
            )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            metrics_registry.increment(
                "http_requests_total",
                {"path": route_family, "method": request.method, "status": "500"},
            )
            logger.exception(
                "request_failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 3),
                    "client_ip": client_ip,
                    "event": "http_request_error",
                    "error": str(exc),
                },
            )
            raise
        finally:
            correlation_id_var.reset(token)
