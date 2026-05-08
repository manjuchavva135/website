"""Celery task: scrape the RBI press release page for new SDL auction PDFs,
parse them with the AP filter, and upsert AP debt events."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Iterable

from shared_py import S3StorageAdapter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import (
    BasisTag,
    DebtEvent,
    DebtEventType,
    DebtInstrument,
    IngestionMode,
    RunStatus,
    SourceDocument,
    SourceDocumentType,
    SourceFetchRun,
)
from worker.celery_app import celery_app
from worker.config import settings
from worker.rbi_ingestion.models import ParsedBorrowingRecord
from worker.rbi_ingestion.pdf_parser import parse_borrowing_records_from_pdf
from worker.rbi_ingestion.press_release_scraper import (
    FetchedAuctionPdf,
    RbiPressReleaseScraper,
)

logger = logging.getLogger(__name__)

_SOURCE_NAME = "rbi_press_release"
_LOOKBACK_FALLBACK_DAYS = 90


@celery_app.task(name="worker.tasks.rbi_ingest.scrape_sdl_auction_press_releases")
def scrape_sdl_auction_press_releases() -> dict[str, object]:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    s3 = S3StorageAdapter(
        endpoint_url=settings.s3_endpoint_url,
        region=settings.s3_region,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        use_ssl=settings.s3_use_ssl,
    )

    since_date = _last_successful_scrape_date(engine) or (
        datetime.now(UTC).date() - timedelta(days=_LOOKBACK_FALLBACK_DAYS)
    )

    scraper = RbiPressReleaseScraper(listing_url=settings.rbi_press_release_url)
    try:
        new_pdfs = scraper.get_new_auction_pdfs(since_date)
    except Exception as exc:  # noqa: BLE001
        _record_run(engine, status=RunStatus.failed, error=str(exc), pdf_count=0)
        raise
    finally:
        scraper.close()

    persisted = 0
    ap_event_count = 0
    for pdf in new_pdfs:
        result = _persist_pdf(engine, s3, pdf)
        if result is not None:
            persisted += 1
            ap_event_count += result

    _record_run(engine, status=RunStatus.succeeded, pdf_count=persisted)
    logger.info(
        "scrape_sdl_auction_press_releases ok: pdfs=%s ap_events=%s since=%s",
        persisted, ap_event_count, since_date.isoformat(),
    )
    return {
        "status": "ok",
        "since_date": since_date.isoformat(),
        "pdfs_processed": persisted,
        "ap_events_persisted": ap_event_count,
    }


# ---------------------------------------------------------------------- #


def _last_successful_scrape_date(engine) -> date | None:  # noqa: ANN001
    with Session(engine) as session:
        run = session.scalar(
            select(SourceFetchRun)
            .where(
                SourceFetchRun.source_name == _SOURCE_NAME,
                SourceFetchRun.status == RunStatus.succeeded,
            )
            .order_by(SourceFetchRun.completed_at.desc().nullslast())
            .limit(1)
        )
        if run is None or run.completed_at is None:
            return None
        return run.completed_at.date()


def _persist_pdf(engine, s3: S3StorageAdapter, pdf: FetchedAuctionPdf) -> int | None:  # noqa: ANN001
    records = parse_borrowing_records_from_pdf(
        payload=pdf.pdf_bytes,
        source_url=pdf.pdf_url,
        source_family="rbi_auction",
    )
    if not records:
        return 0

    checksum = hashlib.sha256(pdf.pdf_bytes).hexdigest()
    storage_key = f"rbi/press_release/{checksum[:2]}/{checksum}.pdf"

    s3.upload_bytes(
        bucket=settings.s3_bucket,
        key=storage_key,
        payload=pdf.pdf_bytes,
        content_type="application/pdf",
    )

    with Session(engine) as session:
        existing = session.scalar(
            select(SourceDocument).where(SourceDocument.checksum_sha256 == checksum)
        )
        if existing is None:
            doc = SourceDocument(
                source_name=_SOURCE_NAME,
                publisher="Reserve Bank of India",
                source_url=pdf.pdf_url,
                title=pdf.title[:500],
                document_type=SourceDocumentType.pdf,
                publication_date=pdf.publication_date,
                checksum_sha256=checksum,
                content_length_bytes=len(pdf.pdf_bytes),
                storage_bucket=settings.s3_bucket,
                storage_key=storage_key,
                review_status="approved",
                ingestion_mode=IngestionMode.auto_fetch,
            )
            session.add(doc)
            session.flush()
        else:
            doc = existing

        ap_count = _upsert_ap_events(session, records, doc.id)
        session.commit()
        return ap_count


def _upsert_ap_events(
    session: Session, records: Iterable[ParsedBorrowingRecord], document_id: int
) -> int:
    count = 0
    for rec in records:
        if "andhra pradesh" not in (rec.state or "").lower():
            continue
        amount = rec.accepted_amount or rec.notified_amount
        if amount is None:
            continue

        instrument = _get_or_create_instrument(session, rec)
        event_type = _map_event_type(rec.event_type)

        existing = session.scalar(
            select(DebtEvent).where(
                DebtEvent.debt_instrument_id == instrument.id,
                DebtEvent.event_type == event_type,
                DebtEvent.event_date == rec.event_date,
                DebtEvent.basis_tag == BasisTag.actual,
                DebtEvent.amount == amount,
            )
        )
        if existing is not None:
            continue

        session.add(
            DebtEvent(
                debt_instrument_id=instrument.id,
                event_type=event_type,
                event_date=rec.event_date,
                basis_tag=BasisTag.actual,
                amount=amount,
                notes=f"source_document_id={document_id}",
            )
        )
        count += 1
    return count


def _get_or_create_instrument(
    session: Session, rec: ParsedBorrowingRecord
) -> DebtInstrument:
    code = (
        f"ap_sdl_{rec.maturity_date.isoformat()}"
        if rec.maturity_date
        else f"ap_sdl_{rec.issue_name[:40].lower().replace(' ', '_')}"
    )
    instrument = session.scalar(
        select(DebtInstrument).where(
            DebtInstrument.source_system == "RBI",
            DebtInstrument.instrument_code == code,
        )
    )
    if instrument is None:
        instrument = DebtInstrument(
            source_system="RBI",
            instrument_code=code,
            instrument_name=rec.issue_name,
            issuer_name="Government of Andhra Pradesh",
            instrument_type="state_development_loan",
            currency="INR",
            coupon_rate=rec.coupon_or_cutoff_yield,
            maturity_date=rec.maturity_date,
            is_active=True,
        )
        session.add(instrument)
        session.flush()
    return instrument


def _map_event_type(event_type: str) -> DebtEventType:
    mapping = {
        "issued": DebtEventType.issue,
        "issue": DebtEventType.issue,
        "notified": DebtEventType.notification,
        "notification": DebtEventType.notification,
        "redeemed": DebtEventType.redemption,
        "redemption": DebtEventType.redemption,
    }
    return mapping.get(event_type.lower() if event_type else "", DebtEventType.issue)


def _record_run(engine, *, status: RunStatus, error: str | None = None, pdf_count: int = 0) -> None:  # noqa: ANN001
    with Session(engine) as session:
        run = SourceFetchRun(
            source_name=_SOURCE_NAME,
            requested_url=settings.rbi_press_release_url,
            status=status,
            error_message=error,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            response_headers_json=f'{{"pdfs_processed": {pdf_count}}}',
        )
        session.add(run)
        session.commit()
