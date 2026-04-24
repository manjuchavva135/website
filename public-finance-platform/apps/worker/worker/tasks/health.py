from __future__ import annotations

from worker.celery_app import celery_app
from worker.health import worker_health


@celery_app.task(name="worker.tasks.health.worker_health")
def worker_health_task() -> dict[str, object]:
    return worker_health(check_external=True)
