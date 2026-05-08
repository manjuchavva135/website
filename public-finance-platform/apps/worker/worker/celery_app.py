from celery import Celery
from celery.schedules import crontab

from worker.config import settings
from worker.observability import configure_logging

configure_logging()

TASK_MODULES = (
    "worker.tasks.health",
    "worker.tasks.rbi_ingest",
    "worker.tasks.manual_upload",
)

celery_app = Celery(
    "public_finance_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=TASK_MODULES,
)

# Twice-weekly scrape of the RBI press release page for new SDL auction PDFs.
# Tuesday and Friday at 03:00 UTC (~08:30 IST, when RBI typically publishes SDL results).
_BEAT_SCHEDULE = {
    "scrape-sdl-auction-press-releases": {
        "task": "worker.tasks.rbi_ingest.scrape_sdl_auction_press_releases",
        "schedule": crontab(hour=3, minute=0, day_of_week="tue,fri"),
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
    beat_schedule=_BEAT_SCHEDULE,
)
