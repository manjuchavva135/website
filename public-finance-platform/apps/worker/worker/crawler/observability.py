from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime


@dataclass(slots=True)
class CrawlMetrics:
    pages_fetched: int = 0
    documents_created: int = 0
    duplicate_documents: int = 0
    fetch_failures: int = 0
    linked_pdfs_discovered: int = 0
    manual_review_documents: int = 0
    raw_uploads: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def get_crawler_logger() -> logging.Logger:
    return logging.getLogger("worker.crawler")


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    payload = {
        "event": event,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        **fields,
    }
    logger.info(json.dumps(payload, default=str, sort_keys=True))