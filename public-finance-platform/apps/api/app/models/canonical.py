from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

SqliteBigInteger = BigInteger().with_variant(Integer, "sqlite")


class BasisTag(StrEnum):
    audited_actual = "audited_actual"
    actual = "actual"
    monthly_actual_provisional = "monthly_actual_provisional"
    quarter_actual = "quarter_actual"
    budget_estimate = "budget_estimate"
    revised_estimate = "revised_estimate"
    projection = "projection"
    scheduled = "scheduled"
    notified = "notified"
    issued = "issued"
    due = "due"
    paid = "paid"
    nowcast = "nowcast"


class SourceDocumentType(StrEnum):
    pdf = "pdf"
    html = "html"
    xlsx = "xlsx"
    csv = "csv"
    json = "json"
    xls = "xls"
    other = "other"


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    partial = "partial"
    skipped = "skipped"


class ParserErrorLevel(StrEnum):
    warning = "warning"
    error = "error"
    fatal = "fatal"


class DebtEventType(StrEnum):
    notification = "notification"
    issue = "issue"
    redemption = "redemption"
    coupon_due = "coupon_due"
    coupon_paid = "coupon_paid"
    principal_due = "principal_due"
    principal_paid = "principal_paid"
    buyback = "buyback"
    rollover = "rollover"


class ReviewActionType(StrEnum):
    approve = "approve"
    reject = "reject"
    flag = "flag"
    comment = "comment"
    release = "release"


class DatasetReleaseStatus(StrEnum):
    draft = "draft"
    published = "published"
    superseded = "superseded"
    revoked = "revoked"


class ReconciliationStatus(StrEnum):
    matched = "matched"
    discrepancy = "discrepancy"
    unresolved = "unresolved"
    ignored = "ignored"


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("source_name", "checksum_sha256", name="uq_source_documents_source_checksum"),
        UniqueConstraint("storage_key", name="uq_source_documents_storage_key"),
        Index("ix_source_documents_source_pub_date", "source_name", "publication_date"),
        Index("ix_source_documents_review_status", "review_status"),
        Index("ix_source_documents_checksum_sha256", "checksum_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    publisher: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[SourceDocumentType] = mapped_column(
        Enum(SourceDocumentType, name="source_document_type", native_enum=False), nullable=False
    )
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fiscal_year_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_length_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(600), nullable=False)
    fetch_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active_version: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fetch_runs: Mapped[list[SourceFetchRun]] = relationship(back_populates="source_document")
    pages: Mapped[list[SourcePage]] = relationship(back_populates="source_document", cascade="all, delete-orphan")
    parser_runs: Mapped[list[ParserRun]] = relationship(back_populates="source_document")
    provenance_links: Mapped[list[ProvenanceLink]] = relationship(back_populates="source_document")
    rows: Mapped[list[SourceRow]] = relationship("SourceRow", back_populates="document")


class SourceFetchRun(Base):
    __tablename__ = "source_fetch_runs"
    __table_args__ = (
        UniqueConstraint(
            "source_name", "requested_url", "fetched_checksum_sha256", name="uq_source_fetch_runs_request_checksum"
        ),
        Index("ix_source_fetch_runs_source_status", "source_name", "status"),
        Index("ix_source_fetch_runs_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    resolved_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="run_status", native_enum=False), nullable=False)
    fetched_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_headers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)

    source_document: Mapped[SourceDocument | None] = relationship(back_populates="fetch_runs")


class SourcePage(Base):
    __tablename__ = "source_pages"
    __table_args__ = (
        UniqueConstraint("source_document_id", "page_number", name="uq_source_pages_document_page"),
        Index("ix_source_pages_document_page", "source_document_id", "page_number"),
        Index("ix_source_pages_row_locator", "source_document_id", "row_start", "row_end"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    page_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source_document: Mapped[SourceDocument] = relationship(back_populates="pages")
    parser_errors: Mapped[list[ParserError]] = relationship(back_populates="source_page")
    provenance_links: Mapped[list[ProvenanceLink]] = relationship(back_populates="source_page")


class ParserRun(Base):
    __tablename__ = "parser_runs"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id", "parser_name", "parser_version", name="uq_parser_runs_document_parser_version"
        ),
        Index("ix_parser_runs_document_status", "source_document_id", "status"),
        Index("ix_parser_runs_parser_name", "parser_name"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(120), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="parser_run_status", native_enum=False), nullable=False)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    rows_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_document: Mapped[SourceDocument] = relationship(back_populates="parser_runs")
    parser_errors: Mapped[list[ParserError]] = relationship(back_populates="parser_run", cascade="all, delete-orphan")


class ParserError(Base):
    __tablename__ = "parser_errors"
    __table_args__ = (
        Index("ix_parser_errors_run_level", "parser_run_id", "error_level"),
        Index("ix_parser_errors_page_row", "source_page_id", "row_number"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    parser_run_id: Mapped[int] = mapped_column(ForeignKey("parser_runs.id", ondelete="CASCADE"), nullable=False)
    source_page_id: Mapped[int | None] = mapped_column(ForeignKey("source_pages.id"), nullable=True)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_level: Mapped[ParserErrorLevel] = mapped_column(
        Enum(ParserErrorLevel, name="parser_error_level", native_enum=False), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parser_run: Mapped[ParserRun] = relationship(back_populates="parser_errors")
    source_page: Mapped[SourcePage | None] = relationship(back_populates="parser_errors")


class BudgetHead(Base):
    __tablename__ = "budget_heads"
    __table_args__ = (
        UniqueConstraint("head_code", name="uq_budget_heads_head_code"),
        Index("ix_budget_heads_parent_id", "parent_id"),
        Index("ix_budget_heads_department_code", "department_code"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("budget_heads.id"), nullable=True)
    head_code: Mapped[str] = mapped_column(String(80), nullable=False)
    head_name: Mapped[str] = mapped_column(String(300), nullable=False)
    head_level: Mapped[str] = mapped_column(String(30), nullable=False)
    major_head: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sub_major_head: Mapped[str | None] = mapped_column(String(20), nullable=True)
    minor_head: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sub_head: Mapped[str | None] = mapped_column(String(40), nullable=True)
    detail_head: Mapped[str | None] = mapped_column(String(40), nullable=True)
    department_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parent: Mapped[BudgetHead | None] = relationship(remote_side="BudgetHead.id")
    spending_rows: Mapped[list[DepartmentSpending]] = relationship(back_populates="budget_head")


class DebtInstrument(Base):
    __tablename__ = "debt_instruments"
    __table_args__ = (
        UniqueConstraint("source_system", "instrument_code", name="uq_debt_instruments_source_code"),
        Index("ix_debt_instruments_maturity_date", "maturity_date"),
        Index("ix_debt_instruments_issuer", "issuer_name"),
        Index("ix_debt_instruments_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    source_system: Mapped[str] = mapped_column(String(80), nullable=False)
    instrument_code: Mapped[str] = mapped_column(String(120), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    instrument_name: Mapped[str] = mapped_column(String(300), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(80), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    coupon_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    events: Mapped[list[DebtEvent]] = relationship(back_populates="debt_instrument", cascade="all, delete-orphan")
    positions: Mapped[list[DebtPosition]] = relationship(back_populates="debt_instrument", cascade="all, delete-orphan")


class DebtEvent(Base):
    __tablename__ = "debt_events"
    __table_args__ = (
        UniqueConstraint(
            "debt_instrument_id", "event_type", "event_date", "basis_tag", "amount", name="uq_debt_events_natural_key"
        ),
        Index("ix_debt_events_type_date", "event_type", "event_date"),
        Index("ix_debt_events_basis", "basis_tag"),
        Index("ix_debt_events_instrument_date", "debt_instrument_id", "event_date"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    debt_instrument_id: Mapped[int] = mapped_column(ForeignKey("debt_instruments.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[DebtEventType] = mapped_column(
        Enum(DebtEventType, name="debt_event_type", native_enum=False), nullable=False
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    basis_tag: Mapped[BasisTag] = mapped_column(Enum(BasisTag, name="basis_tag", native_enum=False), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    units: Mapped[str | None] = mapped_column(String(40), nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    debt_instrument: Mapped[DebtInstrument] = relationship(back_populates="events")
    provenance_links: Mapped[list[ProvenanceLink]] = relationship(
        "ProvenanceLink",
        primaryjoin="and_(foreign(ProvenanceLink.target_id)==DebtEvent.id, ProvenanceLink.target_table=='debt_events')",
        viewonly=True,
    )


class DebtPosition(Base):
    __tablename__ = "debt_positions"
    __table_args__ = (
        UniqueConstraint(
            "debt_instrument_id", "as_of_date", "basis_tag", name="uq_debt_positions_instrument_date_basis"
        ),
        Index("ix_debt_positions_as_of_basis", "as_of_date", "basis_tag"),
        Index("ix_debt_positions_instrument", "debt_instrument_id"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    debt_instrument_id: Mapped[int] = mapped_column(ForeignKey("debt_instruments.id", ondelete="CASCADE"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    basis_tag: Mapped[BasisTag] = mapped_column(Enum(BasisTag, name="basis_tag_position", native_enum=False), nullable=False)
    outstanding_principal: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    accrued_interest: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    face_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    debt_instrument: Mapped[DebtInstrument] = relationship(back_populates="positions")
    provenance_links: Mapped[list[ProvenanceLink]] = relationship(
        "ProvenanceLink",
        primaryjoin="and_(foreign(ProvenanceLink.target_id)==DebtPosition.id, ProvenanceLink.target_table=='debt_positions')",
        viewonly=True,
    )


class FiscalMetric(Base):
    __tablename__ = "fiscal_metrics"
    __table_args__ = (
        UniqueConstraint(
            "metric_code", "period_start", "period_end", "basis_tag", "department_code",
            name="uq_fiscal_metrics_natural_key"
        ),
        Index("ix_fiscal_metrics_metric_period_basis", "metric_code", "period_start", "basis_tag"),
        Index("ix_fiscal_metrics_department", "department_code"),
        Index("ix_fiscal_metrics_fiscal_year", "fiscal_year"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(300), nullable=False)
    metric_group: Mapped[str] = mapped_column(String(100), nullable=False)
    basis_tag: Mapped[BasisTag] = mapped_column(Enum(BasisTag, name="basis_tag_fiscal", native_enum=False), nullable=False)
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="INR crore")
    department_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    provenance_links: Mapped[list[ProvenanceLink]] = relationship(
        "ProvenanceLink",
        primaryjoin="and_(foreign(ProvenanceLink.target_id)==FiscalMetric.id, ProvenanceLink.target_table=='fiscal_metrics')",
        viewonly=True,
    )


class DepartmentSpending(Base):
    __tablename__ = "department_spending"
    __table_args__ = (
        UniqueConstraint(
            "department_code", "budget_head_id", "period_start", "period_end", "basis_tag",
            name="uq_department_spending_natural_key"
        ),
        Index("ix_department_spending_department_period", "department_code", "period_start"),
        Index("ix_department_spending_basis", "basis_tag"),
        Index("ix_department_spending_budget_head", "budget_head_id"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    department_code: Mapped[str] = mapped_column(String(40), nullable=False)
    department_name: Mapped[str] = mapped_column(String(300), nullable=False)
    budget_head_id: Mapped[int | None] = mapped_column(ForeignKey("budget_heads.id"), nullable=True)
    spending_category: Mapped[str] = mapped_column(String(80), nullable=False)
    basis_tag: Mapped[BasisTag] = mapped_column(Enum(BasisTag, name="basis_tag_spending", native_enum=False), nullable=False)
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="INR crore")

    budget_head: Mapped[BudgetHead | None] = relationship(back_populates="spending_rows")
    provenance_links: Mapped[list[ProvenanceLink]] = relationship(
        "ProvenanceLink",
        primaryjoin="and_(foreign(ProvenanceLink.target_id)==DepartmentSpending.id, ProvenanceLink.target_table=='department_spending')",
        viewonly=True,
    )


class ProvenanceLink(Base):
    __tablename__ = "provenance_links"
    __table_args__ = (
        UniqueConstraint(
            "target_table", "target_id", "source_document_id", "source_page_id", "row_number", "column_name",
            name="uq_provenance_links_target_locator"
        ),
        Index("ix_provenance_links_target", "target_table", "target_id"),
        Index("ix_provenance_links_document_page_row", "source_document_id", "source_page_id", "row_number"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    target_table: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False)
    source_page_id: Mapped[int | None] = mapped_column(ForeignKey("source_pages.id"), nullable=True)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    column_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cell_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quoted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_run_id: Mapped[int | None] = mapped_column(ForeignKey("parser_runs.id"), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_document: Mapped[SourceDocument] = relationship(back_populates="provenance_links")
    source_page: Mapped[SourcePage | None] = relationship(back_populates="provenance_links")
    parser_run: Mapped[ParserRun | None] = relationship()

class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"
    __table_args__ = (
        UniqueConstraint("run_name", "started_at", name="uq_reconciliation_runs_name_started"),
        Index("ix_reconciliation_runs_status", "status"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    run_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="reconciliation_run_status", native_enum=False), nullable=False)
    scope_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list[ReconciliationResult]] = relationship(back_populates="reconciliation_run", cascade="all, delete-orphan")


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"
    __table_args__ = (
        UniqueConstraint(
            "reconciliation_run_id", "entity_table", "entity_key", name="uq_reconciliation_results_run_entity"
        ),
        Index("ix_reconciliation_results_status", "status"),
        Index("ix_reconciliation_results_entity", "entity_table", "entity_key"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    reconciliation_run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False)
    entity_table: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus, name="reconciliation_status", native_enum=False), nullable=False
    )
    left_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    right_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    difference_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reconciliation_run: Mapped[ReconciliationRun] = relationship(back_populates="results")


class ReviewAction(Base):
    __tablename__ = "review_actions"
    __table_args__ = (
        Index("ix_review_actions_entity", "entity_table", "entity_id"),
        Index("ix_review_actions_status", "review_status"),
        Index("ix_review_actions_actor", "actor_email"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    entity_table: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action_type: Mapped[ReviewActionType] = mapped_column(
        Enum(ReviewActionType, name="review_action_type", native_enum=False), nullable=False
    )
    review_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    acted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)

    source_document: Mapped[SourceDocument | None] = relationship()


class DatasetRelease(Base):
    __tablename__ = "dataset_releases"
    __table_args__ = (
        UniqueConstraint("dataset_name", "release_version", name="uq_dataset_releases_dataset_version"),
        Index("ix_dataset_releases_status", "status"),
        Index("ix_dataset_releases_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(SqliteBigInteger, primary_key=True, autoincrement=True)
    dataset_name: Mapped[str] = mapped_column(String(120), nullable=False)
    release_version: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[DatasetReleaseStatus] = mapped_column(
        Enum(DatasetReleaseStatus, name="dataset_release_status", native_enum=False), nullable=False
    )
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest_storage_key: Mapped[str | None] = mapped_column(String(600), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(DatasetRelease, "before_update")
def _prevent_release_update(mapper, connection, target) -> None:
    raise ValueError("Dataset releases are immutable and cannot be updated")


@event.listens_for(DatasetRelease, "before_delete")
def _prevent_release_delete(mapper, connection, target) -> None:
    raise ValueError("Dataset releases are immutable and cannot be deleted")
