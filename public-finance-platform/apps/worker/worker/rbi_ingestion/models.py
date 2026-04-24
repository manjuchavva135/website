from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RbiSourceSpec:
    source_family: str
    url: str


@dataclass(frozen=True, slots=True)
class ParsedBorrowingRecord:
    source_url: str
    source_family: str
    event_date: date
    state: str
    issue_name: str
    series: str | None
    notified_amount: Decimal | None
    accepted_amount: Decimal | None
    underwriting_notified_amount: Decimal | None
    tenor: str | None
    maturity_date: date | None
    coupon_or_cutoff_yield: Decimal | None
    event_type: str
    parser_confidence: float
    notes: str | None = None
