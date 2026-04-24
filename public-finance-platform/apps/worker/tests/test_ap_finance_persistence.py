from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import FiscalMetric, ProvenanceLink
from worker.ap_finance_ingestion.models import ParsedFiscalMetricRecord, ProvenanceLocator
from worker.ap_finance_ingestion.persistence import APFinancePersistence


def _fiscal_record() -> ParsedFiscalMetricRecord:
    return ParsedFiscalMetricRecord(
        metric_code="fm_revenuereceipts",
        metric_name="Revenue Receipts",
        metric_group="finance_summary",
        basis_tag="budget_estimate",
        fiscal_year="2025-26",
        period_start=date(2025, 4, 1),
        period_end=date(2026, 3, 31),
        value_inr_crore=Decimal("120000"),
        unit="INR crore",
        department_code=None,
        source_family="budget_in_brief",
        parser_confidence=1.0,
        notes=None,
        provenance=ProvenanceLocator(
            source_url="https://finance.ap.gov.in/budget.html",
            page_number=1,
            row_number=2,
            row_label="Revenue Receipts",
            quoted_text="Revenue Receipts | 120000",
        ),
    )


def test_persistence_upserts_metric_and_provenance_idempotently() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionFactory() as session:
        persistence = APFinancePersistence(session)
        record = _fiscal_record()

        doc = persistence.upsert_source_document(
            source_url=record.provenance.source_url,
            source_family=record.source_family,
            payload=b"dummy",
            content_type="text/html",
        )

        first = persistence.upsert_fiscal_metric(doc, record)
        second = persistence.upsert_fiscal_metric(doc, record)
        session.commit()

        assert first.id == second.id

        metric_count = session.execute(select(FiscalMetric)).scalars().all()
        links = session.execute(select(ProvenanceLink)).scalars().all()
        assert len(metric_count) == 1
        assert len(links) == 1
