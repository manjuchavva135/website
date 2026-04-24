from __future__ import annotations

from dataclasses import asdict, dataclass

from worker.crawler.observability import get_crawler_logger, log_event


@dataclass(slots=True)
class RbiIngestionMetrics:
    pages_fetched: int = 0
    pdfs_fetched: int = 0
    records_parsed: int = 0
    instruments_upserted: int = 0
    events_upserted: int = 0
    duplicate_events: int = 0
    manual_review_tasks: int = 0
    source_context_records: int = 0
    fetch_failures: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def emit_pipeline_event(event: str, **fields: object) -> None:
    log_event(get_crawler_logger(), event, **fields)
