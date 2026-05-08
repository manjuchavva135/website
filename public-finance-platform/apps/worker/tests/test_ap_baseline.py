"""Tests for the AP baseline ingestion path: AP filter, reconciliation, CLI scaffolding."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from worker.rbi_ingestion.ap_reconciliation import reconcile
from worker.rbi_ingestion.models import ParsedBorrowingRecord
from worker.rbi_ingestion.outstanding_parser import OutstandingPosition
from worker.rbi_ingestion.pdf_parser import _is_ap_row


def test_is_ap_row_matches_common_variants() -> None:
    assert _is_ap_row("Andhra Pradesh")
    assert _is_ap_row("ANDHRA  PRADESH SDL 2036")
    assert _is_ap_row("A.P. SDL 2030")
    assert _is_ap_row("Government of A.P.")


def test_is_ap_row_rejects_other_states() -> None:
    assert not _is_ap_row("Maharashtra SDL 2030")
    assert not _is_ap_row("Tamil Nadu SDL")
    assert not _is_ap_row("")


def _record(
    *,
    issue: str,
    event_type: str,
    amount: Decimal,
    state: str = "Andhra Pradesh",
    maturity: date | None = None,
) -> ParsedBorrowingRecord:
    return ParsedBorrowingRecord(
        source_url="test://",
        source_family="rbi_auction",
        event_date=date(2025, 1, 15),
        state=state,
        issue_name=issue,
        series=issue,
        notified_amount=None,
        accepted_amount=amount,
        underwriting_notified_amount=None,
        tenor=None,
        maturity_date=maturity,
        coupon_or_cutoff_yield=None,
        event_type=event_type,
        parser_confidence=0.9,
    )


def test_reconcile_prefers_authoritative_outstanding() -> None:
    auction_records = [
        _record(issue="AP SDL 2036", event_type="issued", amount=Decimal("500"), maturity=date(2036, 4, 1)),
    ]
    outstanding = [
        OutstandingPosition(
            state="Andhra Pradesh",
            instrument_code="ap sdl 2036|2036-04-01",
            instrument_name="AP SDL 2036",
            maturity_date=date(2036, 4, 1),
            coupon_rate=Decimal("7.25"),
            outstanding_principal=Decimal("450"),  # less than issued
            as_of_date=date(2026, 1, 23),
            source_url="test://outstanding",
        ),
    ]
    summary = reconcile(auction_records, outstanding)
    # Authoritative outstanding wins, computed-from-events is suppressed.
    assert summary.instruments_authoritative == 1
    assert summary.instruments_computed == 0
    assert summary.total_outstanding == Decimal("450")


def test_reconcile_computes_from_events_when_no_authoritative() -> None:
    auction_records = [
        _record(issue="AP SDL 2030", event_type="issued", amount=Decimal("1000"), maturity=date(2030, 4, 1)),
        _record(issue="AP SDL 2030", event_type="issued", amount=Decimal("500"), maturity=date(2030, 4, 1)),
        _record(issue="AP SDL 2030", event_type="redeemed", amount=Decimal("200"), maturity=date(2030, 4, 1)),
    ]
    summary = reconcile(auction_records, [])
    assert summary.instruments_computed == 1
    assert summary.total_outstanding == Decimal("1300")
    assert summary.positions[0].source == "computed_from_events"


def test_reconcile_drops_non_ap_records() -> None:
    auction_records = [
        _record(issue="Maharashtra SDL", event_type="issued", amount=Decimal("999"), state="Maharashtra"),
        _record(issue="AP SDL 2032", event_type="issued", amount=Decimal("100"), maturity=date(2032, 4, 1)),
    ]
    summary = reconcile(auction_records, [])
    assert summary.auction_events_dropped == 1
    assert summary.total_outstanding == Decimal("100")
