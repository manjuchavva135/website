"""RBI press-release scraper task. Phase 3 wires the actual scraper logic."""

from __future__ import annotations

from worker.celery_app import celery_app


@celery_app.task(name="worker.tasks.rbi_ingest.scrape_sdl_auction_press_releases")
def scrape_sdl_auction_press_releases() -> dict[str, object]:
    # Implementation lands in Phase 3 (worker.rbi_ingestion.press_release_scraper).
    return {"status": "not_implemented"}
