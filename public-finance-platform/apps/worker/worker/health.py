from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import redis
from sqlalchemy import create_engine, text

from worker.config import settings


def worker_health(*, check_external: bool = True) -> dict[str, Any]:
    checks: dict[str, str] = {
        "configuration": "ok",
    }
    status = "ok"

    if check_external:
        try:
            engine = create_engine(settings.database_url, pool_pre_ping=True)
            with engine.connect() as connection:
                connection.execute(text("select 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"
            status = "degraded"

        try:
            client = redis.Redis.from_url(settings.celery_broker_url, socket_connect_timeout=1, socket_timeout=1)
            client.ping()
            checks["broker"] = "ok"
        except redis.RedisError as exc:
            checks["broker"] = f"error: {exc}"
            status = "degraded"

    return {
        "service": "worker",
        "status": status,
        "environment": settings.env,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Worker health check")
    parser.add_argument("--skip-external", action="store_true", help="Skip DB and broker checks")
    args = parser.parse_args()

    payload = worker_health(check_external=not args.skip_external)
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
