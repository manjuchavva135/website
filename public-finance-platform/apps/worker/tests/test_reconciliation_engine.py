from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base
from app.models import (
    BasisTag,
    DebtEvent,
    DebtEventType,
    DebtInstrument,
    DebtPosition,
    FiscalMetric,
    ProvenanceLink,
    ReconciliationResult,
    ReconciliationRun,
    SourceDocument,
    SourceDocumentType,
)
from worker.reconciliation.engine import AndhraReconciliationService


def _seed_source_document(session: Session, source_name: str, checksum_suffix: str) -> int:
    row = SourceDocument(
        source_name=source_name,
        publisher="Seed",
        source_url=f"https://example.org/{source_name}/{checksum_suffix}",
        canonical_url=f"https://example.org/{source_name}/{checksum_suffix}",
        title=f"{source_name}-{checksum_suffix}",
        document_type=SourceDocumentType.pdf,
        mime_type="application/pdf",
        publication_date=date(2026, 3, 31),
        effective_date=None,
        fiscal_year_label="2025-26",
        checksum_sha256=("0" * 60) + checksum_suffix.zfill(4),
        content_length_bytes=10,
        storage_bucket="seed",
        storage_key=f"seed/{source_name}/{checksum_suffix}.pdf",
        fetch_etag=None,
        parser_version="seed",
        review_status="approved",
        review_notes=None,
        is_active_version=True,
    )
    session.add(row)
    session.flush()
    return int(row.id)


def _link_provenance(session: Session, source_document_id: int, target_table: str, target_id: int, idx: int) -> None:
    session.add(
        ProvenanceLink(
            id=idx,
            target_table=target_table,
            target_id=target_id,
            source_document_id=source_document_id,
            source_page_id=None,
            row_number=idx,
            row_label=None,
            column_name=None,
            cell_ref=None,
            quoted_text=None,
            parser_run_id=None,
            confidence_score=Decimal("1.0"),
            notes="seed",
        )
    )


def test_reconciliation_persists_conflicts_and_human_readable_notes() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionFactory() as session:
        cag_doc = _seed_source_document(session, "cag", "1")
        ap_doc = _seed_source_document(session, "ap_finance", "2")

        session.add(
            DebtInstrument(
                id=1,
                source_system="AP_FINANCE",
                instrument_code="stock_total",
                isin=None,
                instrument_name="Outstanding Debt Stock",
                issuer_name="Government of Andhra Pradesh",
                instrument_type="STATE_LOAN",
                currency="INR",
                coupon_rate=None,
                issue_date=None,
                maturity_date=None,
                is_active=True,
            )
        )
        session.add(
            DebtInstrument(
                id=2,
                source_system="AP_FINANCE",
                instrument_code="stock_total_alt",
                isin=None,
                instrument_name="Outstanding Debt Stock Alt",
                issuer_name="Government of Andhra Pradesh",
                instrument_type="STATE_LOAN",
                currency="INR",
                coupon_rate=None,
                issue_date=None,
                maturity_date=None,
                is_active=True,
            )
        )
        session.add_all(
            [
                DebtPosition(
                    id=1,
                    debt_instrument_id=1,
                    as_of_date=date(2026, 3, 31),
                    basis_tag=BasisTag.audited_actual,
                    outstanding_principal=Decimal("1000"),
                    accrued_interest=None,
                    face_value=None,
                    market_value=None,
                ),
                DebtPosition(
                    id=2,
                    debt_instrument_id=2,
                    as_of_date=date(2026, 3, 31),
                    basis_tag=BasisTag.audited_actual,
                    outstanding_principal=Decimal("940"),
                    accrued_interest=None,
                    face_value=None,
                    market_value=None,
                ),
            ]
        )
        _link_provenance(session, cag_doc, "debt_positions", 1, 1)
        _link_provenance(session, ap_doc, "debt_positions", 2, 2)

        session.add_all(
            [
                FiscalMetric(
                    id=1,
                    metric_code="receipts_total",
                    metric_name="Receipts",
                    metric_group="receipts",
                    basis_tag=BasisTag.audited_actual,
                    fiscal_year="2025-26",
                    period_start=date(2025, 4, 1),
                    period_end=date(2026, 3, 31),
                    value=Decimal("500"),
                    unit="INR crore",
                    department_code=None,
                    notes=None,
                ),
                FiscalMetric(
                    id=2,
                    metric_code="receipts_total",
                    metric_name="Receipts",
                    metric_group="receipts",
                    basis_tag=BasisTag.audited_actual,
                    fiscal_year="2025-26",
                    period_start=date(2025, 4, 1),
                    period_end=date(2026, 3, 31),
                    value=Decimal("530"),
                    unit="INR crore",
                    department_code=None,
                    notes=None,
                ),
            ]
        )
        _link_provenance(session, cag_doc, "fiscal_metrics", 1, 3)
        _link_provenance(session, ap_doc, "fiscal_metrics", 2, 4)

        session.commit()

        service = AndhraReconciliationService(session)
        summary = service.run(fiscal_year="2025-26", as_of_date=date(2026, 3, 31))

        assert summary["status"] == "ok"
        assert summary["conflicts"] >= 2

        conflicts = session.execute(
            select(ReconciliationResult).where(ReconciliationResult.status == "discrepancy")
        ).scalars().all()
        assert conflicts
        assert any("Official source conflict" in (row.notes or "") for row in conflicts)


def test_rollforward_scheduled_isolation_and_interest_principal_separation() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionFactory() as session:
        cag_doc = _seed_source_document(session, "cag", "10")
        rbi_doc = _seed_source_document(session, "rbi", "11")
        ap_doc = _seed_source_document(session, "ap_finance", "12")

        session.add(
            DebtInstrument(
                id=1,
                source_system="AP_FINANCE",
                instrument_code="stock_total",
                isin=None,
                instrument_name="Outstanding Debt Stock",
                issuer_name="Government of Andhra Pradesh",
                instrument_type="STATE_LOAN",
                currency="INR",
                coupon_rate=None,
                issue_date=None,
                maturity_date=None,
                is_active=True,
            )
        )
        session.add(
            DebtPosition(
                id=1,
                debt_instrument_id=1,
                as_of_date=date(2026, 3, 31),
                basis_tag=BasisTag.audited_actual,
                outstanding_principal=Decimal("1000"),
                accrued_interest=None,
                face_value=None,
                market_value=None,
            )
        )
        _link_provenance(session, cag_doc, "debt_positions", 1, 1)

        session.add_all(
            [
                DebtEvent(
                    id=1,
                    debt_instrument_id=1,
                    event_type=DebtEventType.issue,
                    event_date=date(2025, 6, 1),
                    basis_tag=BasisTag.issued,
                    amount=Decimal("130"),
                    units="INR crore",
                    counterparty="AP",
                    notes="rbi full auction result",
                ),
                DebtEvent(
                    id=2,
                    debt_instrument_id=1,
                    event_type=DebtEventType.issue,
                    event_date=date(2025, 6, 1),
                    basis_tag=BasisTag.issued,
                    amount=Decimal("150"),
                    units="INR crore",
                    counterparty="AP",
                    notes="ap aggregate",
                ),
                DebtEvent(
                    id=3,
                    debt_instrument_id=1,
                    event_type=DebtEventType.notification,
                    event_date=date(2025, 8, 1),
                    basis_tag=BasisTag.scheduled,
                    amount=Decimal("500"),
                    units="INR crore",
                    counterparty="AP",
                    notes="rbi calendar",
                ),
                DebtEvent(
                    id=4,
                    debt_instrument_id=1,
                    event_type=DebtEventType.principal_paid,
                    event_date=date(2025, 12, 1),
                    basis_tag=BasisTag.paid,
                    amount=Decimal("20"),
                    units="INR crore",
                    counterparty="AP",
                    notes="actual repayment",
                ),
                DebtEvent(
                    id=5,
                    debt_instrument_id=1,
                    event_type=DebtEventType.coupon_due,
                    event_date=date(2025, 12, 1),
                    basis_tag=BasisTag.due,
                    amount=Decimal("9"),
                    units="INR crore",
                    counterparty="AP",
                    notes="interest due",
                ),
            ]
        )
        _link_provenance(session, rbi_doc, "debt_events", 1, 2)
        _link_provenance(session, ap_doc, "debt_events", 2, 3)
        _link_provenance(session, rbi_doc, "debt_events", 3, 4)

        session.commit()

        service = AndhraReconciliationService(session)
        service.run(fiscal_year="2025-26", as_of_date=date(2026, 3, 31))

        results = session.execute(
            select(ReconciliationResult).where(ReconciliationResult.entity_table == "andhra_reconciliation")
        ).scalars().all()
        values = {row.entity_key: row.left_value for row in results}

        assert values["new_debt_issued_in_fy:issued"] == "130.00"
        assert values["scheduled_debt_pipeline:scheduled"] == "500.00"
        assert values["interest_due:due"] == "9.00"
        assert values["current_outstanding_debt:actual"] == "1110.00"


def test_basis_series_separation_receipts_views_are_distinct() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionFactory() as session:
        cag_doc = _seed_source_document(session, "cag", "20")
        ap_doc = _seed_source_document(session, "ap_finance", "21")

        session.add_all(
            [
                FiscalMetric(
                    id=1,
                    metric_code="receipts_total",
                    metric_name="Receipts",
                    metric_group="receipts",
                    basis_tag=BasisTag.audited_actual,
                    fiscal_year="2025-26",
                    period_start=date(2025, 4, 1),
                    period_end=date(2026, 3, 31),
                    value=Decimal("700"),
                    unit="INR crore",
                    department_code=None,
                    notes=None,
                ),
                FiscalMetric(
                    id=2,
                    metric_code="receipts_total",
                    metric_name="Receipts",
                    metric_group="receipts",
                    basis_tag=BasisTag.budget_estimate,
                    fiscal_year="2025-26",
                    period_start=date(2025, 4, 1),
                    period_end=date(2026, 3, 31),
                    value=Decimal("760"),
                    unit="INR crore",
                    department_code=None,
                    notes=None,
                ),
            ]
        )
        _link_provenance(session, cag_doc, "fiscal_metrics", 1, 1)
        _link_provenance(session, ap_doc, "fiscal_metrics", 2, 2)

        session.commit()
        service = AndhraReconciliationService(session)
        service.run(fiscal_year="2025-26", as_of_date=date(2026, 3, 31))

        rows = session.execute(
            select(ReconciliationResult).where(ReconciliationResult.entity_key.like("receipts_view:%"))
        ).scalars().all()
        keys = {row.entity_key for row in rows}
        assert "receipts_view:audited_actual" in keys
        assert "receipts_view:budget_estimate" in keys


def test_reconciliation_run_and_results_are_persisted() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionFactory() as session:
        service = AndhraReconciliationService(session)
        service.run(fiscal_year="2025-26", as_of_date=date(2026, 3, 31))

        run_count = session.execute(select(ReconciliationRun)).scalars().all()
        result_count = session.execute(select(ReconciliationResult)).scalars().all()
        assert len(run_count) == 1
        assert len(result_count) >= 4
