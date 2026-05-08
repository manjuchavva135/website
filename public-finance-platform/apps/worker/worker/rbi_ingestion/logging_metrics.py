from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

_logger = logging.getLogger("worker.rbi_ingestion")


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
    _logger.info("rbi_ingestion.%s %s", event, fields)
