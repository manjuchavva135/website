"""Reconciliation: combine RBI auction events with authoritative outstanding
positions to produce a final view of Andhra Pradesh's outstanding SDL debt.

Authoritative-source rule: when an OutstandingPosition exists for an
instrument, it overrides anything we computed from auction events. For
instruments with no explicit outstanding row, we synthesize one by summing
issuances minus redemptions from the auction events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from worker.rbi_ingestion.models import ParsedBorrowingRecord
from worker.rbi_ingestion.outstanding_parser import OutstandingPosition


@dataclass(frozen=True, slots=True)
class ReconciledPosition:
    instrument_code: str
    instrument_name: str
    outstanding_principal: Decimal
    maturity_date: date | None
    coupon_rate: Decimal | None
    as_of_date: date | None
    source: str  # "outstanding_pdf" | "computed_from_events"
    underlying_event_count: int = 0


@dataclass(slots=True)
class ReconciliationSummary:
    total_outstanding: Decimal = Decimal("0")
    instruments_authoritative: int = 0
    instruments_computed: int = 0
    auction_events_total: int = 0
    auction_events_dropped: int = 0
    positions: list[ReconciledPosition] = field(default_factory=list)


def reconcile(
    auction_records: list[ParsedBorrowingRecord],
    outstanding_positions: list[OutstandingPosition],
) -> ReconciliationSummary:
    summary = ReconciliationSummary()
    summary.auction_events_total = len(auction_records)

    authoritative: dict[str, ReconciledPosition] = {}
    for pos in outstanding_positions:
        reconciled = ReconciledPosition(
            instrument_code=pos.instrument_code,
            instrument_name=pos.instrument_name,
            outstanding_principal=pos.outstanding_principal,
            maturity_date=pos.maturity_date,
            coupon_rate=pos.coupon_rate,
            as_of_date=pos.as_of_date,
            source="outstanding_pdf",
        )
        authoritative[_key_for_position(pos)] = reconciled
        summary.instruments_authoritative += 1

    computed: dict[str, _RunningTotal] = {}
    for rec in auction_records:
        if rec.state and "andhra pradesh" not in rec.state.lower():
            summary.auction_events_dropped += 1
            continue
        key = _key_for_record(rec)
        if key in authoritative:
            # Authoritative outstanding row already covers this instrument; ignore events.
            continue
        running = computed.setdefault(key, _RunningTotal(name=rec.issue_name))
        amount = rec.accepted_amount or rec.notified_amount
        if amount is None:
            continue
        if rec.event_type in {"issued", "notified"}:
            running.issued += amount
        elif rec.event_type in {"redeemed", "matured"}:
            running.redeemed += amount
        running.events += 1
        if rec.maturity_date and running.maturity is None:
            running.maturity = rec.maturity_date
        if rec.coupon_or_cutoff_yield and running.coupon is None:
            running.coupon = rec.coupon_or_cutoff_yield

    for key, running in computed.items():
        outstanding = running.issued - running.redeemed
        if outstanding <= 0:
            continue
        reconciled = ReconciledPosition(
            instrument_code=key,
            instrument_name=running.name,
            outstanding_principal=outstanding,
            maturity_date=running.maturity,
            coupon_rate=running.coupon,
            as_of_date=datetime.utcnow().date(),
            source="computed_from_events",
            underlying_event_count=running.events,
        )
        authoritative[key] = reconciled
        summary.instruments_computed += 1

    summary.positions = sorted(
        authoritative.values(), key=lambda p: (p.maturity_date or date.max, p.instrument_code)
    )
    summary.total_outstanding = sum(
        (p.outstanding_principal for p in summary.positions), start=Decimal("0")
    )
    return summary


@dataclass(slots=True)
class _RunningTotal:
    name: str
    issued: Decimal = Decimal("0")
    redeemed: Decimal = Decimal("0")
    events: int = 0
    maturity: date | None = None
    coupon: Decimal | None = None


def _key_for_position(pos: OutstandingPosition) -> str:
    return pos.instrument_code.strip().lower()


def _key_for_record(rec: ParsedBorrowingRecord) -> str:
    base = (rec.series or rec.issue_name or "ap_sdl").strip().lower()
    if rec.maturity_date:
        return f"{base}|{rec.maturity_date.isoformat()}"
    return base
