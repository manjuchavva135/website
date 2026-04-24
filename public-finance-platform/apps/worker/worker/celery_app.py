from celery import Celery

from worker.config import settings
from worker.observability import configure_logging

configure_logging()

TASK_MODULES = (
    "worker.tasks.health",
    "worker.tasks.ingest",
    "worker.tasks.ap_finance_ingest",
    "worker.tasks.rbi_ingest",
)

celery_app = Celery(
    "public_finance_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=TASK_MODULES,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
