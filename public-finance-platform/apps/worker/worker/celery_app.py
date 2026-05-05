from celery import Celery
from celery.schedules import crontab

from worker.config import settings
from worker.observability import configure_logging

configure_logging()

TASK_MODULES = (
    "worker.tasks.health",
    "worker.tasks.ingest",
    "worker.tasks.ap_finance_ingest",
    "worker.tasks.rbi_ingest",
    "worker.tasks.manual_upload",
)

celery_app = Celery(
    "public_finance_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=TASK_MODULES,
)

# Weekly schedule: every Monday at 02:00 UTC (approx 07:30 IST).
# Only active after baseline-v1 is published — set AUTO_FETCHERS_ENABLED=true to enable.
_WEEKLY_BEAT_SCHEDULE = {
    "fetch-official-sources-weekly": {
        "task": "worker.tasks.ingest.fetch_official_sources",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),
    },
    "fetch-ap-finance-weekly": {
        "task": "worker.tasks.ap_finance_ingest.fetch_ap_finance_data",
        "schedule": crontab(hour=2, minute=15, day_of_week=1),
    },
    "fetch-rbi-borrowing-weekly": {
        "task": "worker.tasks.rbi_ingest.fetch_rbi_borrowing_data",
        "schedule": crontab(hour=2, minute=30, day_of_week=1),
    },
}

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule=_WEEKLY_BEAT_SCHEDULE if settings.auto_fetchers_enabled else {},
)
