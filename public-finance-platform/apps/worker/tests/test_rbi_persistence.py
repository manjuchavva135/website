from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from worker.rbi_ingestion.models import ParsedBorrowingRecord
from worker.rbi_ingestion.persistence import RbiPersistence


def _record() -> ParsedBorrowingRecord:
    return ParsedBorrowingRecord(
        source_url="https://www.rbi.org.in/sdl/result.pdf",
        source_family="sdl_auction_result",
        event_date=date(2026, 4, 24),
        state="Andhra Pradesh",
        issue_name="AP SDL 2036",
        series="2036",
        notified_amount=Decimal("2000"),
        accepted_amount=Decimal("1920"),
        underwriting_notified_amount=Decimal("250"),
        tenor="10Y",
        maturity_date=date(2036, 4, 24),
        coupon_or_cutoff_yield=Decimal("7.42"),
        event_type="issued",
        parser_confidence=0.95,
        notes=None,
    )


def test_idempotent_upsert_for_instruments_and_events() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    persistence = RbiPersistence(session_factory=SessionFactory)
    record = _record()

    first = persistence.upsert_borrowing_record(record)
    second = persistence.upsert_borrowing_record(record)

    assert first[0] == second[0]
    assert first[1] == second[1]
    assert first[2] is True
    assert second[2] is False


def test_manual_review_task_is_persisted() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    persistence = RbiPersistence(session_factory=SessionFactory)
    document_id = persistence.create_manual_review_task(
        source_url="https://www.rbi.org.in/challenge",
        source_family="sdl_auction_result",
        reason="body:captcha; header:cf-ray",
    )

    assert document_id is not None
