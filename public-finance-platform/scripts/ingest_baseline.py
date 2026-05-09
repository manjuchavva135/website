"""Persist parsed RBI + Outstanding data into SQLite for the baseline release.

Walks Data_website/{Rbi,Outstanding_securities_state}, runs the appropriate
parser on each PDF, and writes records directly via SQLAlchemy. Provenance
links are emitted for every fiscal_metric and debt_position so the public
API can surface the source-row context.

Re-running is idempotent — each document is keyed by (source_name, sha256)
and previously-ingested rows are not duplicated.
"""
from __future__ import annotations

import hashlib
import re
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_engine, SessionLocal
from app.models import (
    BasisTag,
    DebtInstrument,
    DebtPosition,
    FiscalMetric,
    ParserRun,
    ProvenanceLink,
    RunStatus,
    SourceDocument,
    SourceDocumentType,
    SourcePage,
    IngestionMode,
)

from worker.config import settings
from worker.rbi_ingestion.outstanding_parser import (
    OutstandingPosition,
    parse_outstanding_securities_bytes,
)
from worker.rbi_ingestion.state_finances_parser import (
    ParsedDebtPositionRecord,
    ParsedFiscalMetricRecord,
    StateFinancesResult,
    parse_state_finances_pdf,
)

REPO = Path(__file__).resolve().parents[2]
DATA_RBI = REPO / "Data_website" / "Rbi"
DATA_OUT = REPO / "Data_website" / "Outstanding_securities_state"


def _parser_run(db: Session, doc_id: int, parser_name: str) -> ParserRun:
    run = ParserRun(
        source_document_id=doc_id,
        parser_name=parser_name,
        parser_version=settings.parser_version,
        status=RunStatus.running,
        rows_extracted=0,
        warnings_count=0,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()
    return run


def _get_or_create_document(
    db: Session,
    *,
    path: Path,
    source_name: str,
    title: str,
    publisher: str,
    publication_date: date | None,
    fiscal_year_label: str | None,
) -> tuple[SourceDocument, bool]:
    payload = path.read_bytes()
    checksum = hashlib.sha256(payload).hexdigest()

    existing = db.scalar(
        select(SourceDocument).where(
            SourceDocument.source_name == source_name,
            SourceDocument.checksum_sha256 == checksum,
        )
    )
    if existing is not None:
        return existing, False

    doc = SourceDocument(
        source_name=source_name,
        publisher=publisher,
        source_url=str(path),
        title=title,
        document_type=SourceDocumentType.pdf,
        mime_type="application/pdf",
        publication_date=publication_date,
        fiscal_year_label=fiscal_year_label,
        checksum_sha256=checksum,
        content_length_bytes=len(payload),
        storage_key=f"local/{path.name}",
        review_status="approved",
        ingestion_mode=IngestionMode.manual_upload,
        is_active_version=True,
    )
    db.add(doc)
    db.flush()
    return doc, True


def _get_or_create_page(db: Session, doc_id: int, page_number: int) -> SourcePage:
    page = db.scalar(
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
        db.add(page)
        db.flush()
    return page


def _persist_fiscal_metric(
    db: Session, rec: ParsedFiscalMetricRecord, doc: SourceDocument, run_id: int
) -> bool:
    period_start = rec.period_start
    period_end = rec.period_end
    existing = db.scalar(
        select(FiscalMetric).where(
            FiscalMetric.metric_code == rec.metric_code,
            FiscalMetric.period_start == period_start,
            FiscalMetric.period_end == period_end,
            FiscalMetric.basis_tag == rec.basis_tag,
            FiscalMetric.department_code == rec.department_code,
        )
    )
    if existing is not None:
        return False

    metric = FiscalMetric(
        metric_code=rec.metric_code,
        metric_name=rec.metric_name,
        metric_group=rec.metric_group,
        basis_tag=BasisTag(rec.basis_tag),
        fiscal_year=rec.fiscal_year,
        period_start=period_start,
        period_end=period_end,
        value=rec.value_inr_crore,
        unit=rec.unit,
        department_code=rec.department_code,
        notes=rec.notes,
    )
    db.add(metric)
    db.flush()

    prov = rec.provenance
    page = _get_or_create_page(db, int(doc.id), prov.page_number if prov else 1)
    db.add(ProvenanceLink(
        target_table="fiscal_metrics",
        target_id=metric.id,
        source_document_id=doc.id,
        source_page_id=page.id,
        row_number=prov.row_number if prov else None,
        row_label=prov.row_label if prov else None,
        quoted_text=prov.quoted_text if prov else None,
        parser_run_id=run_id,
        confidence_score=Decimal(str(rec.parser_confidence)),
    ))
    return True


def _get_or_create_instrument(
    db: Session, *, source_system: str, code: str, name: str, issuer: str,
    isin: str | None = None, coupon: Decimal | None = None,
    issue_date: date | None = None, maturity_date: date | None = None,
) -> DebtInstrument:
    inst = db.scalar(
        select(DebtInstrument).where(
            DebtInstrument.source_system == source_system,
            DebtInstrument.instrument_code == code,
        )
    )
    if inst is None:
        inst = DebtInstrument(
            source_system=source_system,
            instrument_code=code,
            isin=isin,
            instrument_name=name,
            issuer_name=issuer,
            instrument_type="state_development_loan",
            currency="INR",
            coupon_rate=coupon,
            issue_date=issue_date,
            maturity_date=maturity_date,
            is_active=True,
        )
        db.add(inst)
        db.flush()
    else:
        # Backfill missing fields without overwriting populated ones.
        if inst.maturity_date is None and maturity_date is not None:
            inst.maturity_date = maturity_date
        if inst.coupon_rate is None and coupon is not None:
            inst.coupon_rate = coupon
        if inst.isin is None and isin is not None:
            inst.isin = isin
    return inst


def _persist_debt_position_stmt22(
    db: Session, rec: ParsedDebtPositionRecord, doc: SourceDocument, run_id: int
) -> bool:
    inst = _get_or_create_instrument(
        db,
        source_system="RBI_STMT22",
        code=rec.instrument_code,
        name=rec.instrument_name,
        issuer="Government of Andhra Pradesh",
        coupon=rec.coupon_rate,
        maturity_date=rec.maturity_date,
    )
    existing = db.scalar(
        select(DebtPosition).where(
            DebtPosition.debt_instrument_id == inst.id,
            DebtPosition.as_of_date == rec.as_of_date,
            DebtPosition.basis_tag == BasisTag(rec.basis_tag),
        )
    )
    if existing is not None:
        return False
    pos = DebtPosition(
        debt_instrument_id=inst.id,
        as_of_date=rec.as_of_date,
        basis_tag=BasisTag(rec.basis_tag),
        outstanding_principal=rec.outstanding_principal_inr_crore,
    )
    db.add(pos)
    db.flush()

    prov = rec.provenance
    page = _get_or_create_page(db, int(doc.id), prov.page_number if prov else 1)
    db.add(ProvenanceLink(
        target_table="debt_positions",
        target_id=pos.id,
        source_document_id=doc.id,
        source_page_id=page.id,
        row_number=prov.row_number if prov else None,
        row_label=prov.row_label if prov else None,
        quoted_text=prov.quoted_text if prov else None,
        parser_run_id=run_id,
        confidence_score=Decimal(str(rec.parser_confidence)),
    ))
    return True


def _persist_outstanding(
    db: Session, rec: OutstandingPosition, doc: SourceDocument, run_id: int
) -> bool:
    inst = _get_or_create_instrument(
        db,
        source_system="RBI_OUTSTANDING",
        code=rec.instrument_code,
        name=rec.instrument_name,
        issuer="Government of Andhra Pradesh",
        isin=rec.instrument_code if rec.instrument_code.startswith("IN") else None,
        coupon=rec.coupon_rate,
        maturity_date=rec.maturity_date,
    )
    existing = db.scalar(
        select(DebtPosition).where(
            DebtPosition.debt_instrument_id == inst.id,
            DebtPosition.as_of_date == rec.as_of_date,
            DebtPosition.basis_tag == BasisTag.actual,
        )
    )
    if existing is not None:
        return False
    pos = DebtPosition(
        debt_instrument_id=inst.id,
        as_of_date=rec.as_of_date or date.today(),
        basis_tag=BasisTag.actual,
        outstanding_principal=rec.outstanding_principal,
    )
    db.add(pos)
    db.flush()

    page = _get_or_create_page(db, int(doc.id), 1)
    db.add(ProvenanceLink(
        target_table="debt_positions",
        target_id=pos.id,
        source_document_id=doc.id,
        source_page_id=page.id,
        row_label=rec.instrument_name,
        parser_run_id=run_id,
        confidence_score=Decimal("1.0"),
    ))
    return True


# --------------------------------------------------------------------------- #
# Per-PDF orchestration                                                       #
# --------------------------------------------------------------------------- #

_STMT_TITLE = {
    "stmt_2": ("RBI State Finances 2025-26 — Statement 2 (Revenue Surplus/Deficit)", "rbi_state_finances"),
    "stmt_13": ("RBI State Finances 2025-26 — Statement 13 (Interest Payments)", "rbi_state_finances"),
    "stmt_16": ("RBI State Finances 2025-26 — Statement 16 (Loans from Centre)", "rbi_state_finances"),
    "stmt_19": ("RBI State Finances 2025-26 — Statement 19 (Outstanding Liabilities)", "rbi_state_finances"),
    "stmt_21": ("RBI State Finances 2025-26 — Statement 21 (Market Borrowings)", "rbi_state_finances"),
    "stmt_22": ("RBI State Finances 2025-26 — Statement 22 (State Government Market Loans)", "rbi_state_finances"),
    "stmt_23": ("RBI State Finances 2025-26 — Statement 23 (Maturity Profile)", "rbi_state_finances"),
    "appendix_1": ("RBI State Finances 2025-26 — Appendix I (Revenue Receipts by Item)", "rbi_state_finances"),
}


def ingest_rbi_pdf(db: Session, path: Path) -> dict:
    payload = path.read_bytes()
    parsed: StateFinancesResult = parse_state_finances_pdf(payload, source_url=str(path))
    title, source_name = _STMT_TITLE.get(
        parsed.statement_id,
        (f"RBI {parsed.statement_id}", "rbi_state_finances"),
    )
    pub_date = date(2026, 1, 23)  # filename embeds 23012026 = publication date
    doc, created = _get_or_create_document(
        db, path=path, source_name=source_name, title=title,
        publisher="Reserve Bank of India",
        publication_date=pub_date, fiscal_year_label="2025-26",
    )
    run = _parser_run(db, int(doc.id), parser_name="rbi_state_finances")
    saved = 0
    for rec in parsed.fiscal_metrics:
        if _persist_fiscal_metric(db, rec, doc, int(run.id)):
            saved += 1
    for rec in parsed.debt_positions:
        if _persist_debt_position_stmt22(db, rec, doc, int(run.id)):
            saved += 1
    run.status = RunStatus.succeeded
    run.rows_extracted = saved
    run.warnings_count = len(parsed.warnings)
    run.completed_at = datetime.now(UTC)
    return {
        "file": path.name, "statement": parsed.statement_id,
        "doc_id": int(doc.id), "doc_created": created,
        "fiscal_metrics": len(parsed.fiscal_metrics),
        "debt_positions": len(parsed.debt_positions),
        "rows_persisted": saved,
        "warnings": parsed.warnings,
    }


def ingest_outstanding_pdf(db: Session, path: Path) -> dict:
    payload = path.read_bytes()
    positions = parse_outstanding_securities_bytes(payload, source_url=str(path))
    doc, created = _get_or_create_document(
        db, path=path, source_name="rbi_outstanding_sgs",
        title="RBI Outstanding State Government Securities (as on May 06, 2026)",
        publisher="Reserve Bank of India",
        publication_date=date(2026, 5, 6), fiscal_year_label="2026-27",
    )
    run = _parser_run(db, int(doc.id), parser_name="rbi_outstanding")
    saved = 0
    for pos in positions:
        if _persist_outstanding(db, pos, doc, int(run.id)):
            saved += 1
    run.status = RunStatus.succeeded
    run.rows_extracted = saved
    run.completed_at = datetime.now(UTC)
    return {
        "file": path.name, "statement": "outstanding",
        "doc_id": int(doc.id), "doc_created": created,
        "positions_parsed": len(positions),
        "rows_persisted": saved,
    }


def main() -> int:
    print(f"DB: {get_engine().url}")
    rbi_pdfs = sorted(DATA_RBI.glob("*.pdf"))
    out_pdfs = sorted(DATA_OUT.glob("*.pdf"))

    print(f"Ingesting {len(rbi_pdfs)} RBI statement PDFs + {len(out_pdfs)} Outstanding PDFs")
    summaries: list[dict] = []
    db = SessionLocal()
    try:
        for path in rbi_pdfs:
            summary = ingest_rbi_pdf(db, path)
            summaries.append(summary)
            print(f"  [{summary['statement']:11}] {summary['file'][:35]:35} "
                  f"metrics={summary['fiscal_metrics']:4} positions={summary['debt_positions']:4} "
                  f"persisted={summary['rows_persisted']:4} {'(new)' if summary['doc_created'] else '(existing)'}")
        for path in out_pdfs:
            summary = ingest_outstanding_pdf(db, path)
            summaries.append(summary)
            print(f"  [outstanding] {summary['file'][:35]:35} "
                  f"positions={summary['positions_parsed']:4} "
                  f"persisted={summary['rows_persisted']:4} {'(new)' if summary['doc_created'] else '(existing)'}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print()
    total_persisted = sum(s["rows_persisted"] for s in summaries)
    print(f"Total rows persisted: {total_persisted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
