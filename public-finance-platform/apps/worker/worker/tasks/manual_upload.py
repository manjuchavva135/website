from __future__ import annotations

import logging
from datetime import UTC, datetime

from shared_py import S3StorageAdapter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import (
    BasisTag,
    DebtEvent,
    DebtEventType,
    DebtInstrument,
    DebtPosition,
    DepartmentSpending,
    FiscalMetric,
    ParserError,
    ParserRun,
    ProvenanceLink,
    RunStatus,
    SourceDocument,
    SourcePage,
)
from worker.celery_app import celery_app
from worker.config import settings
from worker.extractors import get_extractor

logger = logging.getLogger(__name__)


@celery_app.task(name="worker.tasks.manual_upload.parse_uploaded_document")
def parse_uploaded_document(*, document_id: int, source_family: str) -> dict[str, object]:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    s3 = S3StorageAdapter(
        endpoint_url=settings.s3_endpoint_url,
        region=settings.s3_region,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        use_ssl=settings.s3_use_ssl,
    )

    with Session(engine) as session:
        doc = session.scalar(select(SourceDocument).where(SourceDocument.id == document_id))
        if doc is None:
            raise ValueError(f"SourceDocument {document_id} not found")

        content = s3.get_object_bytes(doc.storage_bucket or settings.s3_bucket, doc.storage_key)
        extractor = get_extractor()

        parser_run = ParserRun(
            source_document_id=document_id,
            parser_name=extractor.name if hasattr(extractor, "name") else "rule_based",
            parser_version=settings.parser_version,
            status=RunStatus.running,
            rows_extracted=0,
            warnings_count=0,
            started_at=datetime.now(UTC),
        )
        session.add(parser_run)
        session.flush()

        try:
            result = extractor.extract(
                content=content,
                document_type=str(doc.document_type),
                source_family=source_family,
                source_url=doc.source_url or "",
            )

            rows_saved = _persist_result(session, result, doc, parser_run.id)

            for warning in result.warnings:
                session.add(ParserError(
                    parser_run_id=parser_run.id,
                    error_level="warning",
                    message=warning[:2000],
                ))

            parser_run.status = RunStatus.succeeded
            parser_run.rows_extracted = rows_saved
            parser_run.warnings_count = len(result.warnings)
            parser_run.completed_at = datetime.now(UTC)

            doc.review_status = "in_review"
            doc.parser_version = settings.parser_version

            session.commit()

            recon_run_id = _maybe_trigger_reconciliation(source_family)

            logger.info(
                "parse_uploaded_document completed document_id=%s rows=%s warnings=%s recon=%s",
                document_id, rows_saved, len(result.warnings), recon_run_id,
            )
            return {
                "status": "ok",
                "document_id": document_id,
                "rows_extracted": rows_saved,
                "reconciliation_run_id": recon_run_id,
            }

        except Exception as exc:
            parser_run.status = RunStatus.failed
            parser_run.completed_at = datetime.now(UTC)
            session.add(ParserError(
                parser_run_id=parser_run.id,
                error_level="fatal",
                message=str(exc)[:2000],
            ))
            session.commit()
            raise


_DEBT_FAMILIES = {"rbi_auction", "outstanding_securities"}


def _maybe_trigger_reconciliation(source_family: str) -> int | None:
    """Re-run AP reconciliation when a debt-related upload lands.

    Reads existing AP DebtEvents + DebtPositions from the DB and rewrites
    a fresh ReconciliationRun. Non-debt uploads (e.g. ap_budget) skip this.
    """
    if source_family not in _DEBT_FAMILIES:
        return None
    try:
        from worker.tasks.reconcile_ap import recompute_ap_reconciliation

        return recompute_ap_reconciliation()
    except Exception as exc:  # noqa: BLE001
        logger.warning("post-upload reconciliation failed: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Persistence helpers                                                          #
# --------------------------------------------------------------------------- #

def _persist_result(session: Session, result, doc: SourceDocument, parser_run_id: int) -> int:
    rows_saved = 0
    rows_saved += _save_fiscal_metrics(session, result.fiscal_metrics, doc, parser_run_id)
    rows_saved += _save_department_spending(session, result.department_spending, doc, parser_run_id)
    rows_saved += _save_debt_events(session, result.debt_events, doc, parser_run_id)
    rows_saved += _save_debt_positions(session, result.debt_positions, doc, parser_run_id)
    rows_saved += _save_borrowing_records(session, result.borrowing_records, doc, parser_run_id)
    return rows_saved


def _get_or_create_page(session: Session, doc_id: int, page_number: int) -> SourcePage:
    page = session.scalar(
        select(SourcePage).where(
            SourcePage.source_document_id == doc_id,
            SourcePage.page_number == page_number,
        )
    )
    if page is None:
        page = SourcePage(
            source_document_id=doc_id,
            page_number=page_number,
            page_label=f"page_{page_number}",
        )
        session.add(page)
        session.flush()
    return page


def _save_fiscal_metrics(session: Session, records: list, doc: SourceDocument, parser_run_id: int) -> int:
    count = 0
    for rec in records:
        try:
            metric = FiscalMetric(
                metric_code=rec.metric_code,
                metric_name=rec.metric_name,
                metric_group=rec.metric_group,
                basis_tag=rec.basis_tag,
                fiscal_year=rec.fiscal_year,
                period_start=rec.period_start,
                period_end=rec.period_end,
                value=rec.value_inr_crore,
                unit=rec.unit,
                department_code=rec.department_code,
                notes=rec.notes,
            )
            session.add(metric)
            session.flush()

            prov = getattr(rec, "provenance", None)
            page_num = getattr(prov, "page_number", 1) if prov else 1
            row_num = getattr(prov, "row_number", None) if prov else None
            page = _get_or_create_page(session, int(doc.id), page_num)

            session.add(ProvenanceLink(
                target_table="fiscal_metrics",
                target_id=metric.id,
                source_document_id=doc.id,
                source_page_id=page.id,
                row_number=row_num,
                row_label=getattr(prov, "row_label", None) if prov else None,
                quoted_text=getattr(prov, "quoted_text", None) if prov else None,
                parser_run_id=parser_run_id,
                confidence_score=getattr(rec, "parser_confidence", None),
            ))
            count += 1
        except Exception:  # noqa: BLE001 — skip duplicate rows
            session.rollback()
    return count


def _save_department_spending(session: Session, records: list, doc: SourceDocument, parser_run_id: int) -> int:
    count = 0
    for rec in records:
        try:
            row = DepartmentSpending(
                department_code=rec.department_code,
                department_name=rec.department_name,
                spending_category=rec.spending_category,
                basis_tag=rec.basis_tag,
                fiscal_year=rec.fiscal_year,
                period_start=rec.period_start,
                period_end=rec.period_end,
                amount=rec.amount_inr_crore,
                unit=rec.unit,
            )
            session.add(row)
            session.flush()

            prov = getattr(rec, "provenance", None)
            page_num = getattr(prov, "page_number", 1) if prov else 1
            page = _get_or_create_page(session, int(doc.id), page_num)

            session.add(ProvenanceLink(
                target_table="department_spending",
                target_id=row.id,
                source_document_id=doc.id,
                source_page_id=page.id,
                row_number=getattr(prov, "row_number", None) if prov else None,
                row_label=getattr(prov, "row_label", None) if prov else None,
                quoted_text=getattr(prov, "quoted_text", None) if prov else None,
                parser_run_id=parser_run_id,
                confidence_score=getattr(rec, "parser_confidence", None),
            ))
            count += 1
        except Exception:  # noqa: BLE001
            session.rollback()
    return count


def _save_debt_events(session: Session, records: list, doc: SourceDocument, parser_run_id: int) -> int:
    count = 0
    for rec in records:
        try:
            instrument = _get_or_create_instrument(
                session,
                source_system="MANUAL",
                code=rec.instrument_code,
                name=rec.instrument_name,
                issuer=rec.issuer_name,
            )
            event = DebtEvent(
                debt_instrument_id=instrument.id,
                event_type=rec.event_type,
                event_date=rec.event_date,
                basis_tag=rec.basis_tag,
                amount=rec.amount_inr_crore,
                notes=rec.notes,
            )
            session.add(event)
            session.flush()

            prov = getattr(rec, "provenance", None)
            page_num = getattr(prov, "page_number", 1) if prov else 1
            page = _get_or_create_page(session, int(doc.id), page_num)

            session.add(ProvenanceLink(
                target_table="debt_events",
                target_id=event.id,
                source_document_id=doc.id,
                source_page_id=page.id,
                row_number=getattr(prov, "row_number", None) if prov else None,
                quoted_text=getattr(prov, "quoted_text", None) if prov else None,
                parser_run_id=parser_run_id,
                confidence_score=getattr(rec, "parser_confidence", None),
            ))
            count += 1
        except Exception:  # noqa: BLE001
            session.rollback()
    return count


def _save_debt_positions(session: Session, records: list, doc: SourceDocument, parser_run_id: int) -> int:
    count = 0
    for rec in records:
        try:
            instrument = _get_or_create_instrument(
                session,
                source_system="MANUAL",
                code=rec.instrument_code,
                name=rec.instrument_name,
                issuer=rec.issuer_name,
            )
            position = DebtPosition(
                debt_instrument_id=instrument.id,
                as_of_date=rec.as_of_date,
                basis_tag=rec.basis_tag,
                outstanding_principal=rec.outstanding_principal_inr_crore,
                accrued_interest=rec.accrued_interest_inr_crore,
                face_value=rec.face_value_inr_crore,
                market_value=rec.market_value_inr_crore,
            )
            session.add(position)
            session.flush()

            prov = getattr(rec, "provenance", None)
            page_num = getattr(prov, "page_number", 1) if prov else 1
            page = _get_or_create_page(session, int(doc.id), page_num)

            session.add(ProvenanceLink(
                target_table="debt_positions",
                target_id=position.id,
                source_document_id=doc.id,
                source_page_id=page.id,
                row_number=getattr(prov, "row_number", None) if prov else None,
                quoted_text=getattr(prov, "quoted_text", None) if prov else None,
                parser_run_id=parser_run_id,
                confidence_score=getattr(rec, "parser_confidence", None),
            ))
            count += 1
        except Exception:  # noqa: BLE001
            session.rollback()
    return count


def _save_borrowing_records(session: Session, records: list, doc: SourceDocument, parser_run_id: int) -> int:
    """Persist RBI ParsedBorrowingRecord as DebtInstrument + DebtEvent pairs."""
    count = 0
    for rec in records:
        try:
            code = f"rbi_{rec.issue_name[:40].lower().replace(' ', '_')}"
            instrument = _get_or_create_instrument(
                session,
                source_system="RBI",
                code=code,
                name=rec.issue_name,
                issuer=f"Government of {rec.state}",
            )
            amount = rec.notified_amount or rec.accepted_amount
            if amount is None:
                continue

            event = DebtEvent(
                debt_instrument_id=instrument.id,
                event_type=rec.event_type,
                event_date=rec.event_date,
                basis_tag=BasisTag.notified,
                amount=amount,
                notes=rec.notes,
            )
            session.add(event)
            session.flush()

            page = _get_or_create_page(session, int(doc.id), 1)
            session.add(ProvenanceLink(
                target_table="debt_events",
                target_id=event.id,
                source_document_id=doc.id,
                source_page_id=page.id,
                parser_run_id=parser_run_id,
                confidence_score=getattr(rec, "parser_confidence", None),
            ))
            count += 1
        except Exception:  # noqa: BLE001
            session.rollback()
    return count


def _get_or_create_instrument(
    session: Session, *, source_system: str, code: str, name: str, issuer: str
) -> DebtInstrument:
    instrument = session.scalar(
        select(DebtInstrument).where(
            DebtInstrument.source_system == source_system,
            DebtInstrument.instrument_code == code,
        )
    )
    if instrument is None:
        instrument = DebtInstrument(
            source_system=source_system,
            instrument_code=code,
            instrument_name=name,
            issuer_name=issuer,
            instrument_type="government_security",
            currency="INR",
            is_active=True,
        )
        session.add(instrument)
        session.flush()
    return instrument
