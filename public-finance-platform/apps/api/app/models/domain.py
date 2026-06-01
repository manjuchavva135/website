from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.canonical import SourceDocument


class ReviewStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Basis(StrEnum):
    audited_actual = "audited_actual"
    revised_estimate = "revised_estimate"
    budget_estimate = "budget_estimate"
    projection = "projection"
    scheduled_debt = "scheduled_debt"
    issued_debt = "issued_debt"


class MetricGroup(StrEnum):
    debt_outstanding = "debt_outstanding"
    debt_issued = "debt_issued"
    debt_pipeline = "debt_pipeline"
    principal_repayment_due = "principal_repayment_due"
    interest_due = "interest_due"
    receipts_tax = "receipts_tax"
    receipts_non_tax = "receipts_non_tax"
    receipts_grants = "receipts_grants"
    expenditure_revenue = "expenditure_revenue"
    expenditure_capital = "expenditure_capital"
    expenditure_departmental = "expenditure_departmental"
    deficit_revenue = "deficit_revenue"
    deficit_fiscal = "deficit_fiscal"
    deficit_primary = "deficit_primary"
class SourceRow(Base):
    __tablename__ = "source_rows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"))
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    row_number: Mapped[int | None] = mapped_column(nullable=True)
    row_label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)

    document: Mapped[SourceDocument] = relationship(back_populates="rows")


class MetricSeries(Base):
    __tablename__ = "metric_series"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    metric_group: Mapped[str] = mapped_column(String(60), index=True)
    unit: Mapped[str] = mapped_column(String(40), default="INR crore")
    state_code: Mapped[str] = mapped_column(String(8), nullable=False, default="AP", server_default="AP", index=True)
    description: Mapped[str] = mapped_column(Text)

    observations: Mapped[list[MetricObservation]] = relationship(back_populates="series", cascade="all, delete")


class MetricObservation(Base):
    __tablename__ = "metric_observations"
    __table_args__ = (
        UniqueConstraint(
            "series_id",
            "period_start",
            "period_end",
            "basis",
            name="uq_metric_observation_series_period_basis",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("metric_series.id", ondelete="CASCADE"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    period_label: Mapped[str] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    basis: Mapped[str] = mapped_column(String(40), index=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"), index=True)
    source_row_id: Mapped[int | None] = mapped_column(ForeignKey("source_rows.id"), nullable=True)
    provenance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    series: Mapped[MetricSeries] = relationship(back_populates="observations")
    source_document: Mapped[SourceDocument] = relationship()
    source_row: Mapped[SourceRow | None] = relationship()


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(120), index=True)
    parser_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChangelogEntry(Base):
    __tablename__ = "changelog_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(200))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
