from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import Base, engine
from app.models import ChangelogEntry, MetricObservation, MetricSeries, SourceDocument


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


def seed_reference_data(db: Session) -> None:
    existing = db.scalar(select(MetricSeries.id).limit(1))
    if existing:
        return

    doc = SourceDocument(
        source_name="seed",
        publisher="Platform bootstrap",
        title="Initial seeded sample",
        source_url="https://example.org/seed",
        document_type="html",
        publication_date=date.today(),
        storage_key="seed/initial.json",
        checksum_sha256="0" * 64,
        parser_version="seed-0.1",
        review_status="approved",
        review_notes="Seeded for local development only",
    )
    db.add(doc)
    db.flush()

    templates = [
        ("ap-outstanding-debt", "Andhra Pradesh Outstanding Debt", "debt_outstanding"),
        ("ap-new-debt-issued", "Andhra Pradesh New Debt Issued", "debt_issued"),
        ("ap-debt-pipeline", "Andhra Pradesh Scheduled Debt Pipeline", "debt_pipeline"),
        ("ap-principal-repayments", "Andhra Pradesh Principal Repayments Due", "principal_repayment_due"),
        ("ap-interest-due", "Andhra Pradesh Interest Due", "interest_due"),
        ("ap-receipts-tax", "Andhra Pradesh Tax Receipts", "receipts_tax"),
        ("ap-receipts-non-tax", "Andhra Pradesh Non-Tax Receipts", "receipts_non_tax"),
        ("ap-receipts-grants", "Andhra Pradesh Grants", "receipts_grants"),
        ("ap-expenditure-revenue", "Andhra Pradesh Revenue Expenditure", "expenditure_revenue"),
        ("ap-expenditure-capital", "Andhra Pradesh Capital Expenditure", "expenditure_capital"),
        (
            "ap-expenditure-departmental",
            "Andhra Pradesh Departmental Expenditure",
            "expenditure_departmental",
        ),
        ("ap-deficit-revenue", "Andhra Pradesh Revenue Deficit", "deficit_revenue"),
        ("ap-deficit-fiscal", "Andhra Pradesh Fiscal Deficit", "deficit_fiscal"),
        ("ap-deficit-primary", "Andhra Pradesh Primary Deficit", "deficit_primary"),
    ]

    for slug, title, group in templates:
        series = MetricSeries(
            slug=slug,
            title=title,
            metric_group=group,
            unit="INR crore",
            description="Sample series for platform bootstrapping. Replace with ingested official values.",
        )
        db.add(series)
        db.flush()

        db.add(
            MetricObservation(
                series_id=series.id,
                period_start=date(2025, 4, 1),
                period_end=date(2026, 3, 31),
                period_label="FY 2025-26",
                amount=Decimal("100.00"),
                currency="INR",
                basis="budget_estimate",
                source_document_id=doc.id,
                source_row_id=None,
                provenance_note="Seed data only",
            )
        )

    db.add(
        ChangelogEntry(
            version="0.1.0",
            title="Initial platform bootstrap",
            details="Created starter datasets, provenance model, and API endpoints.",
        )
    )

    db.commit()
