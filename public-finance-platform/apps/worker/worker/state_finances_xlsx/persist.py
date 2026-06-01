"""Write parsed xlsx records to the canonical fact tables.

Mirrors the persistence pattern of ``rbi_ingestion/persist_baseline.py``: open
a session, register a SourceDocument + ParserRun for provenance, then upsert
FiscalMetric / DebtInstrument / DebtPosition rows. Provenance links are
written for every fact so the API's ``provenance`` endpoint keeps working.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

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
)
from app.models.canonical import IngestionMode
from worker.config import settings
from worker.state_finances_xlsx.records import DebtInstrumentRow, FiscalMetricRow

PARSER_NAME = "state_finances_xlsx"


@dataclass
class IngestStats:
    file: str
    fiscal_metrics_inserted: int = 0
    fiscal_metrics_updated: int = 0
    debt_instruments_inserted: int = 0
    debt_positions_inserted: int = 0
    debt_positions_updated: int = 0
    skipped: int = 0


def _file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _document_type_for(path: Path) -> SourceDocumentType:
    suffix = path.suffix.lower()
    if suffix == ".xls":
        return SourceDocumentType.xls
    return SourceDocumentType.xlsx


def get_or_create_source_document(session: Session, path: Path, *, title: str) -> SourceDocument:
    checksum = _file_checksum(path)
    existing = session.scalar(
        select(SourceDocument).where(SourceDocument.checksum_sha256 == checksum)
    )
    if existing is not None:
        return existing
    storage_key = f"local-baseline/{path.name}"
    doc = SourceDocument(
        source_name="rbi_state_finances_xlsx",
        publisher="Reserve Bank of India",
        source_url=None,
        title=title,
        document_type=_document_type_for(path),
        mime_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if path.suffix.lower() == ".xlsx"
            else "application/vnd.ms-excel"
        ),
        publication_date=datetime.now(UTC).date(),
        checksum_sha256=checksum,
        content_length_bytes=path.stat().st_size,
        storage_bucket=None,
        storage_key=storage_key,
        review_status="approved",
        ingestion_mode=IngestionMode.manual_upload,
        is_active_version=True,
    )
    session.add(doc)
    session.flush()
    return doc


def start_parser_run(session: Session, doc: SourceDocument) -> ParserRun:
    run = ParserRun(
        source_document_id=doc.id,
        parser_name=PARSER_NAME,
        parser_version=settings.parser_version,
        status=RunStatus.running,
    )
    session.add(run)
    session.flush()
    return run


def persist_fiscal_metrics(
    session: Session,
    doc: SourceDocument,
    parser_run: ParserRun,
    rows: Iterable[FiscalMetricRow],
    stats: IngestStats,
) -> None:
    for row in rows:
        try:
            basis = BasisTag(row.basis_tag)
        except ValueError:
            stats.skipped += 1
            continue

        existing = session.scalar(
            select(FiscalMetric).where(
                FiscalMetric.state_code == row.state_code,
                FiscalMetric.metric_code == row.metric_code,
                FiscalMetric.period_start == row.period_start,
                FiscalMetric.period_end == row.period_end,
                FiscalMetric.basis_tag == basis,
                FiscalMetric.department_code == row.department_code,
            )
        )
        if existing is None:
            metric = FiscalMetric(
                state_code=row.state_code,
                metric_code=row.metric_code,
                metric_name=row.metric_name,
                metric_group=row.metric_group,
                basis_tag=basis,
                fiscal_year=row.fiscal_year,
                period_start=row.period_start,
                period_end=row.period_end,
                value=row.value,
                unit=row.unit,
                unit_scale=row.unit_scale,
                department_code=row.department_code,
                notes=row.notes,
            )
            session.add(metric)
            session.flush()
            stats.fiscal_metrics_inserted += 1
        else:
            existing.value = row.value
            existing.unit = row.unit
            existing.unit_scale = row.unit_scale
            existing.metric_name = row.metric_name
            existing.metric_group = row.metric_group
            metric = existing
            stats.fiscal_metrics_updated += 1

        if row.provenance is not None:
            session.add(
                ProvenanceLink(
                    target_table="fiscal_metrics",
                    target_id=metric.id,
                    source_document_id=doc.id,
                    row_number=row.provenance.row_number,
                    row_label=row.provenance.row_label,
                    column_name=row.provenance.column_label,
                    cell_ref=f"{row.provenance.sheet_name}!R{row.provenance.row_number}C{row.provenance.column_index}",
                    quoted_text=row.provenance.quoted_text,
                    parser_run_id=parser_run.id,
                )
            )


def persist_debt_instruments(
    session: Session,
    doc: SourceDocument,
    parser_run: ParserRun,
    rows: Iterable[DebtInstrumentRow],
    stats: IngestStats,
) -> None:
    for row in rows:
        instrument = session.scalar(
            select(DebtInstrument).where(
                DebtInstrument.source_system == "RBI",
                DebtInstrument.instrument_code == row.instrument_code,
            )
        )
        if instrument is None:
            instrument = DebtInstrument(
                source_system="RBI",
                instrument_code=row.instrument_code,
                isin=row.instrument_code,
                instrument_name=row.instrument_name,
                issuer_name=row.issuer_name,
                issuer_state_code=row.issuer_state_code,
                instrument_type=row.instrument_type,
                currency="INR",
                coupon_rate=row.coupon_rate,
                issue_date=row.issue_date,
                maturity_date=row.maturity_date,
                is_active=True,
            )
            session.add(instrument)
            session.flush()
            stats.debt_instruments_inserted += 1
        else:
            # Refresh derived fields in case earlier loads were missing them.
            if instrument.issuer_state_code is None and row.issuer_state_code:
                instrument.issuer_state_code = row.issuer_state_code
            if instrument.coupon_rate is None and row.coupon_rate is not None:
                instrument.coupon_rate = row.coupon_rate
            if instrument.maturity_date is None and row.maturity_date is not None:
                instrument.maturity_date = row.maturity_date
            if instrument.issue_date is None and row.issue_date is not None:
                instrument.issue_date = row.issue_date

        existing_pos = session.scalar(
            select(DebtPosition).where(
                DebtPosition.debt_instrument_id == instrument.id,
                DebtPosition.as_of_date == row.as_of_date,
                DebtPosition.basis_tag == BasisTag.actual,
            )
        )
        if existing_pos is None:
            pos = DebtPosition(
                debt_instrument_id=instrument.id,
                as_of_date=row.as_of_date,
                basis_tag=BasisTag.actual,
                outstanding_principal=row.outstanding_principal,
            )
            session.add(pos)
            session.flush()
            stats.debt_positions_inserted += 1
            if row.provenance is not None:
                session.add(
                    ProvenanceLink(
                        target_table="debt_positions",
                        target_id=pos.id,
                        source_document_id=doc.id,
                        row_number=row.provenance.row_number,
                        row_label=row.provenance.row_label,
                        column_name=row.provenance.column_label,
                        cell_ref=f"{row.provenance.sheet_name}!R{row.provenance.row_number}",
                        parser_run_id=parser_run.id,
                    )
                )
        else:
            existing_pos.outstanding_principal = row.outstanding_principal
            stats.debt_positions_updated += 1


def finish_parser_run(
    session: Session,
    parser_run: ParserRun,
    stats: IngestStats,
    *,
    status: RunStatus = RunStatus.succeeded,
) -> None:
    parser_run.status = status
    parser_run.rows_extracted = (
        stats.fiscal_metrics_inserted
        + stats.fiscal_metrics_updated
        + stats.debt_positions_inserted
        + stats.debt_positions_updated
    )
    parser_run.completed_at = datetime.now(UTC)


def open_session() -> Session:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    return Session(engine)
