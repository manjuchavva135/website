from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import BasisTag, DebtEvent, DebtEventType, DebtInstrument, ReviewAction, ReviewActionType, SourceDocument
from worker.rbi_ingestion.models import ParsedBorrowingRecord


class RbiPersistence:
    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

    def upsert_borrowing_record(self, record: ParsedBorrowingRecord) -> tuple[int, int, bool]:
        with self.session_factory() as session:
            instrument = self._upsert_instrument(session=session, record=record)
            event, created = self._upsert_event(session=session, instrument_id=int(instrument.id), record=record)
            session.commit()
            return int(instrument.id), int(event.id), created

    def create_manual_review_task(self, source_url: str, source_family: str, reason: str) -> int | None:
        with self.session_factory() as session:
            document = SourceDocument(
                source_name="rbi",
                publisher="Reserve Bank of India",
                source_url=source_url,
                canonical_url=source_url,
                title=f"Manual review required for {source_family}",
                document_type="html",
                publication_date=datetime.now(UTC).date(),
                checksum_sha256=f"manual-review-{abs(hash((source_url, reason)))}",
                content_length_bytes=0,
                storage_bucket="manual-review",
                storage_key=f"manual-review/{source_family}/{abs(hash(source_url))}.txt",
                parser_version="rbi-ingestion",
                review_status="needs_manual_review",
                review_notes=reason[:1000],
            )
            session.add(document)
            session.flush()

            action = ReviewAction(
                id=self._next_pk(session, ReviewAction),
                entity_table="source_documents",
                entity_id=int(document.id),
                action_type=ReviewActionType.flag,
                review_status="needs_manual_review",
                actor_email="system@public-finance.local",
                comments=reason[:1000],
                source_document_id=int(document.id),
            )
            session.add(action)
            session.commit()
            return int(document.id)

    def create_source_context_record(self, source_url: str, source_family: str, note: str) -> int:
        with self.session_factory() as session:
            document = SourceDocument(
                source_name="rbi",
                publisher="Reserve Bank of India",
                source_url=source_url,
                canonical_url=source_url,
                title=f"Context source for {source_family}",
                document_type="html",
                publication_date=datetime.now(UTC).date(),
                checksum_sha256=f"context-{abs(hash((source_url, source_family, note)))}",
                content_length_bytes=0,
                storage_bucket="context",
                storage_key=f"context/{source_family}/{abs(hash(source_url))}.txt",
                parser_version="rbi-ingestion",
                review_status="pending",
                review_notes=note[:1000],
            )
            session.add(document)
            session.commit()
            return int(document.id)

    def _upsert_instrument(self, session: Session, record: ParsedBorrowingRecord) -> DebtInstrument:
        instrument_code = self._build_instrument_code(record)
        existing = session.execute(
            select(DebtInstrument).where(
                DebtInstrument.source_system == "RBI",
                DebtInstrument.instrument_code == instrument_code,
            )
        ).scalar_one_or_none()

        maturity = record.maturity_date
        issue_date = record.event_date
        coupon_rate = record.coupon_or_cutoff_yield

        if existing is None:
            created = DebtInstrument(
                id=self._next_pk(session, DebtInstrument),
                source_system="RBI",
                instrument_code=instrument_code,
                isin=None,
                instrument_name=record.issue_name,
                issuer_name=record.state,
                instrument_type="SDL",
                currency="INR",
                coupon_rate=coupon_rate,
                issue_date=issue_date,
                maturity_date=maturity,
                is_active=True,
            )
            session.add(created)
            session.flush()
            return created

        existing.instrument_name = record.issue_name
        existing.issuer_name = record.state
        existing.coupon_rate = coupon_rate or existing.coupon_rate
        existing.issue_date = issue_date or existing.issue_date
        existing.maturity_date = maturity or existing.maturity_date
        session.flush()
        return existing

    def _upsert_event(self, session: Session, instrument_id: int, record: ParsedBorrowingRecord) -> tuple[DebtEvent, bool]:
        amount = self._resolve_amount(record)
        basis_tag = self._map_basis_tag(record.event_type)
        debt_event_type = self._map_debt_event_type(record.event_type)

        existing = session.execute(
            select(DebtEvent).where(
                DebtEvent.debt_instrument_id == instrument_id,
                DebtEvent.event_type == debt_event_type,
                DebtEvent.event_date == record.event_date,
                DebtEvent.basis_tag == basis_tag,
                DebtEvent.amount == amount,
            )
        ).scalar_one_or_none()

        notes = self._build_event_notes(record)
        if existing is None:
            created = DebtEvent(
                id=self._next_pk(session, DebtEvent),
                debt_instrument_id=instrument_id,
                event_type=debt_event_type,
                event_date=record.event_date,
                basis_tag=basis_tag,
                amount=amount,
                units="INR crore",
                counterparty=record.state,
                notes=notes,
            )
            session.add(created)
            session.flush()
            return created, True

        existing.counterparty = record.state
        existing.notes = notes
        session.flush()
        return existing, False

    @staticmethod
    def _build_instrument_code(record: ParsedBorrowingRecord) -> str:
        tenor = (record.tenor or "na").replace(" ", "").lower()
        return f"rbi-{record.state.lower().replace(' ', '-')}-{record.issue_name.lower().replace(' ', '-')}-{tenor}"

    @staticmethod
    def _resolve_amount(record: ParsedBorrowingRecord) -> Decimal:
        if record.event_type == "issued" and record.accepted_amount is not None:
            return record.accepted_amount
        if record.notified_amount is not None:
            return record.notified_amount
        if record.accepted_amount is not None:
            return record.accepted_amount
        return Decimal("0")

    @staticmethod
    def _map_basis_tag(event_type: str) -> BasisTag:
        mapping = {
            "scheduled": BasisTag.scheduled,
            "notified": BasisTag.notified,
            "issued": BasisTag.issued,
        }
        return mapping.get(event_type, BasisTag.notified)

    @staticmethod
    def _map_debt_event_type(event_type: str) -> DebtEventType:
        mapping = {
            "scheduled": DebtEventType.notification,
            "notified": DebtEventType.notification,
            "issued": DebtEventType.issue,
        }
        return mapping.get(event_type, DebtEventType.notification)

    @staticmethod
    def _build_event_notes(record: ParsedBorrowingRecord) -> str:
        notes = [
            f"source_family={record.source_family}",
            f"confidence={record.parser_confidence}",
        ]
        if record.underwriting_notified_amount is not None:
            notes.append(f"underwriting_notified_amount={record.underwriting_notified_amount}")
        if record.coupon_or_cutoff_yield is not None:
            notes.append(f"coupon_or_cutoff_yield={record.coupon_or_cutoff_yield}")
        if record.notes:
            notes.append(record.notes)
        return "; ".join(notes)

    @staticmethod
    def _next_pk(session: Session, model: type) -> int | None:
        if session.bind is None or session.bind.dialect.name != "sqlite":
            return None
        current_max = session.execute(select(func.max(model.id))).scalar_one()
        return int(current_max or 0) + 1
