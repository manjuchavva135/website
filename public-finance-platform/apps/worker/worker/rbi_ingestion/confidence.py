from __future__ import annotations

from worker.rbi_ingestion.models import ParsedBorrowingRecord


def score_record_confidence(record: ParsedBorrowingRecord) -> float:
    total = 9
    present = 0

    present += 1 if record.event_date else 0
    present += 1 if record.state else 0
    present += 1 if record.issue_name else 0
    present += 1 if record.notified_amount is not None else 0
    present += 1 if record.accepted_amount is not None else 0
    present += 1 if record.tenor else 0
    present += 1 if record.maturity_date else 0
    present += 1 if record.coupon_or_cutoff_yield is not None else 0
    present += 1 if record.event_type in {"scheduled", "notified", "issued"} else 0

    return round(present / total, 4)
