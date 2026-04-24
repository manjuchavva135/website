"""canonical schema

Revision ID: 20260424_0002
Revises: 20260424_0001
Create Date: 2026-04-24

"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0002"
down_revision = "20260424_0001"
branch_labels = None
depends_on = None


source_document_type = sa.Enum(
    "pdf",
    "html",
    "xlsx",
    "csv",
    "json",
    "xls",
    "other",
    name="source_document_type",
    native_enum=False,
)

run_status = sa.Enum(
    "pending",
    "running",
    "succeeded",
    "failed",
    "partial",
    "skipped",
    name="run_status",
    native_enum=False,
)

parser_run_status = sa.Enum(
    "pending",
    "running",
    "succeeded",
    "failed",
    "partial",
    "skipped",
    name="parser_run_status",
    native_enum=False,
)

parser_error_level = sa.Enum(
    "warning",
    "error",
    "fatal",
    name="parser_error_level",
    native_enum=False,
)

debt_event_type = sa.Enum(
    "notification",
    "issue",
    "redemption",
    "coupon_due",
    "coupon_paid",
    "principal_due",
    "principal_paid",
    "buyback",
    "rollover",
    name="debt_event_type",
    native_enum=False,
)

basis_tag = sa.Enum(
    "audited_actual",
    "actual",
    "monthly_actual_provisional",
    "quarter_actual",
    "budget_estimate",
    "revised_estimate",
    "projection",
    "scheduled",
    "notified",
    "issued",
    "due",
    "paid",
    "nowcast",
    name="basis_tag",
    native_enum=False,
)

basis_tag_position = sa.Enum(
    "audited_actual",
    "actual",
    "monthly_actual_provisional",
    "quarter_actual",
    "budget_estimate",
    "revised_estimate",
    "projection",
    "scheduled",
    "notified",
    "issued",
    "due",
    "paid",
    "nowcast",
    name="basis_tag_position",
    native_enum=False,
)

basis_tag_fiscal = sa.Enum(
    "audited_actual",
    "actual",
    "monthly_actual_provisional",
    "quarter_actual",
    "budget_estimate",
    "revised_estimate",
    "projection",
    "scheduled",
    "notified",
    "issued",
    "due",
    "paid",
    "nowcast",
    name="basis_tag_fiscal",
    native_enum=False,
)

basis_tag_spending = sa.Enum(
    "audited_actual",
    "actual",
    "monthly_actual_provisional",
    "quarter_actual",
    "budget_estimate",
    "revised_estimate",
    "projection",
    "scheduled",
    "notified",
    "issued",
    "due",
    "paid",
    "nowcast",
    name="basis_tag_spending",
    native_enum=False,
)

reconciliation_run_status = sa.Enum(
    "pending",
    "running",
    "succeeded",
    "failed",
    "partial",
    "skipped",
    name="reconciliation_run_status",
    native_enum=False,
)

reconciliation_status = sa.Enum(
    "matched",
    "discrepancy",
    "unresolved",
    "ignored",
    name="reconciliation_status",
    native_enum=False,
)

review_action_type = sa.Enum(
    "approve",
    "reject",
    "flag",
    "comment",
    "release",
    name="review_action_type",
    native_enum=False,
)

dataset_release_status = sa.Enum(
    "draft",
    "published",
    "superseded",
    "revoked",
    name="dataset_release_status",
    native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table("source_documents") as batch_op:
        batch_op.add_column(sa.Column("canonical_url", sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column("mime_type", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("effective_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("fiscal_year_label", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("content_length_bytes", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("storage_bucket", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("fetch_etag", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("is_active_version", sa.Boolean(), nullable=False, server_default=sa.text("true"))
        )
        batch_op.alter_column(
            "document_type",
            existing_type=sa.String(length=40),
            type_=source_document_type,
            existing_nullable=False,
        )
        batch_op.alter_column("publisher", existing_type=sa.String(length=120), type_=sa.String(length=200))
        batch_op.alter_column("title", existing_type=sa.String(length=300), type_=sa.String(length=500))
        batch_op.alter_column("storage_key", existing_type=sa.String(length=500), type_=sa.String(length=600))
        batch_op.alter_column(
            "parser_version",
            existing_type=sa.String(length=40),
            type_=sa.String(length=60),
            nullable=True,
        )
        batch_op.alter_column(
            "review_status",
            existing_type=sa.String(length=20),
            type_=sa.String(length=30),
            existing_nullable=False,
        )
        batch_op.create_index("ix_source_documents_source_pub_date", ["source_name", "publication_date"], unique=False)
        batch_op.create_index("ix_source_documents_review_status", ["review_status"], unique=False)
        batch_op.create_unique_constraint(
            "uq_source_documents_source_checksum",
            ["source_name", "checksum_sha256"],
        )

    op.create_table(
        "source_fetch_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("requested_url", sa.String(length=1000), nullable=False),
        sa.Column("resolved_url", sa.String(length=1000), nullable=True),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("status", run_status, nullable=False),
        sa.Column("fetched_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("response_headers_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_document_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name",
            "requested_url",
            "fetched_checksum_sha256",
            name="uq_source_fetch_runs_request_checksum",
        ),
    )
    op.create_index("ix_source_fetch_runs_source_status", "source_fetch_runs", ["source_name", "status"], unique=False)
    op.create_index("ix_source_fetch_runs_started_at", "source_fetch_runs", ["started_at"], unique=False)

    op.create_table(
        "source_pages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("page_label", sa.String(length=100), nullable=True),
        sa.Column("page_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("row_start", sa.Integer(), nullable=True),
        sa.Column("row_end", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_document_id", "page_number", name="uq_source_pages_document_page"),
    )
    op.create_index("ix_source_pages_document_page", "source_pages", ["source_document_id", "page_number"], unique=False)
    op.create_index("ix_source_pages_row_locator", "source_pages", ["source_document_id", "row_start", "row_end"], unique=False)

    op.create_table(
        "parser_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("parser_name", sa.String(length=120), nullable=False),
        sa.Column("parser_version", sa.String(length=60), nullable=False),
        sa.Column("status", parser_run_status, nullable=False),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("rows_extracted", sa.Integer(), nullable=False),
        sa.Column("warnings_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_document_id",
            "parser_name",
            "parser_version",
            name="uq_parser_runs_document_parser_version",
        ),
    )
    op.create_index("ix_parser_runs_document_status", "parser_runs", ["source_document_id", "status"], unique=False)
    op.create_index("ix_parser_runs_parser_name", "parser_runs", ["parser_name"], unique=False)

    op.create_table(
        "parser_errors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parser_run_id", sa.BigInteger(), nullable=False),
        sa.Column("source_page_id", sa.BigInteger(), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("column_name", sa.String(length=200), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_level", parser_error_level, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parser_run_id"], ["parser_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_page_id"], ["source_pages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parser_errors_run_level", "parser_errors", ["parser_run_id", "error_level"], unique=False)
    op.create_index("ix_parser_errors_page_row", "parser_errors", ["source_page_id", "row_number"], unique=False)

    op.create_table(
        "budget_heads",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("head_code", sa.String(length=80), nullable=False),
        sa.Column("head_name", sa.String(length=300), nullable=False),
        sa.Column("head_level", sa.String(length=30), nullable=False),
        sa.Column("major_head", sa.String(length=20), nullable=True),
        sa.Column("sub_major_head", sa.String(length=20), nullable=True),
        sa.Column("minor_head", sa.String(length=20), nullable=True),
        sa.Column("sub_head", sa.String(length=40), nullable=True),
        sa.Column("detail_head", sa.String(length=40), nullable=True),
        sa.Column("department_code", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["parent_id"], ["budget_heads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("head_code", name="uq_budget_heads_head_code"),
    )
    op.create_index("ix_budget_heads_parent_id", "budget_heads", ["parent_id"], unique=False)
    op.create_index("ix_budget_heads_department_code", "budget_heads", ["department_code"], unique=False)

    op.create_table(
        "debt_instruments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_system", sa.String(length=80), nullable=False),
        sa.Column("instrument_code", sa.String(length=120), nullable=False),
        sa.Column("isin", sa.String(length=32), nullable=True),
        sa.Column("instrument_name", sa.String(length=300), nullable=False),
        sa.Column("issuer_name", sa.String(length=200), nullable=False),
        sa.Column("instrument_type", sa.String(length=80), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("coupon_rate", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "instrument_code", name="uq_debt_instruments_source_code"),
    )
    op.create_index("ix_debt_instruments_maturity_date", "debt_instruments", ["maturity_date"], unique=False)
    op.create_index("ix_debt_instruments_issuer", "debt_instruments", ["issuer_name"], unique=False)
    op.create_index("ix_debt_instruments_active", "debt_instruments", ["is_active"], unique=False)

    op.create_table(
        "debt_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("debt_instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", debt_event_type, nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("basis_tag", basis_tag, nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("units", sa.String(length=40), nullable=True),
        sa.Column("counterparty", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["debt_instrument_id"], ["debt_instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "debt_instrument_id",
            "event_type",
            "event_date",
            "basis_tag",
            "amount",
            name="uq_debt_events_natural_key",
        ),
    )
    op.create_index("ix_debt_events_type_date", "debt_events", ["event_type", "event_date"], unique=False)
    op.create_index("ix_debt_events_basis", "debt_events", ["basis_tag"], unique=False)
    op.create_index("ix_debt_events_instrument_date", "debt_events", ["debt_instrument_id", "event_date"], unique=False)

    op.create_table(
        "debt_positions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("debt_instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("basis_tag", basis_tag_position, nullable=False),
        sa.Column("outstanding_principal", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("accrued_interest", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("face_value", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("market_value", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["debt_instrument_id"], ["debt_instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "debt_instrument_id",
            "as_of_date",
            "basis_tag",
            name="uq_debt_positions_instrument_date_basis",
        ),
    )
    op.create_index("ix_debt_positions_as_of_basis", "debt_positions", ["as_of_date", "basis_tag"], unique=False)
    op.create_index("ix_debt_positions_instrument", "debt_positions", ["debt_instrument_id"], unique=False)

    op.create_table(
        "fiscal_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("metric_code", sa.String(length=100), nullable=False),
        sa.Column("metric_name", sa.String(length=300), nullable=False),
        sa.Column("metric_group", sa.String(length=100), nullable=False),
        sa.Column("basis_tag", basis_tag_fiscal, nullable=False),
        sa.Column("fiscal_year", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("department_code", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "metric_code",
            "period_start",
            "period_end",
            "basis_tag",
            "department_code",
            name="uq_fiscal_metrics_natural_key",
        ),
    )
    op.create_index(
        "ix_fiscal_metrics_metric_period_basis",
        "fiscal_metrics",
        ["metric_code", "period_start", "basis_tag"],
        unique=False,
    )
    op.create_index("ix_fiscal_metrics_department", "fiscal_metrics", ["department_code"], unique=False)
    op.create_index("ix_fiscal_metrics_fiscal_year", "fiscal_metrics", ["fiscal_year"], unique=False)

    op.create_table(
        "department_spending",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("department_code", sa.String(length=40), nullable=False),
        sa.Column("department_name", sa.String(length=300), nullable=False),
        sa.Column("budget_head_id", sa.BigInteger(), nullable=True),
        sa.Column("spending_category", sa.String(length=80), nullable=False),
        sa.Column("basis_tag", basis_tag_spending, nullable=False),
        sa.Column("fiscal_year", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["budget_head_id"], ["budget_heads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "department_code",
            "budget_head_id",
            "period_start",
            "period_end",
            "basis_tag",
            name="uq_department_spending_natural_key",
        ),
    )
    op.create_index(
        "ix_department_spending_department_period",
        "department_spending",
        ["department_code", "period_start"],
        unique=False,
    )
    op.create_index("ix_department_spending_basis", "department_spending", ["basis_tag"], unique=False)
    op.create_index("ix_department_spending_budget_head", "department_spending", ["budget_head_id"], unique=False)

    op.create_table(
        "provenance_links",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("target_table", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("source_page_id", sa.BigInteger(), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("row_label", sa.String(length=300), nullable=True),
        sa.Column("column_name", sa.String(length=200), nullable=True),
        sa.Column("cell_ref", sa.String(length=50), nullable=True),
        sa.Column("quoted_text", sa.Text(), nullable=True),
        sa.Column("parser_run_id", sa.BigInteger(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["parser_run_id"], ["parser_runs.id"]),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_page_id"], ["source_pages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "target_table",
            "target_id",
            "source_document_id",
            "source_page_id",
            "row_number",
            "column_name",
            name="uq_provenance_links_target_locator",
        ),
    )
    op.create_index("ix_provenance_links_target", "provenance_links", ["target_table", "target_id"], unique=False)
    op.create_index(
        "ix_provenance_links_document_page_row",
        "provenance_links",
        ["source_document_id", "source_page_id", "row_number"],
        unique=False,
    )

    op.create_table(
        "reconciliation_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_name", sa.String(length=120), nullable=False),
        sa.Column("rule_version", sa.String(length=60), nullable=False),
        sa.Column("status", reconciliation_run_status, nullable=False),
        sa.Column("scope_json", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_name", "started_at", name="uq_reconciliation_runs_name_started"),
    )
    op.create_index("ix_reconciliation_runs_status", "reconciliation_runs", ["status"], unique=False)

    op.create_table(
        "reconciliation_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("reconciliation_run_id", sa.BigInteger(), nullable=False),
        sa.Column("entity_table", sa.String(length=80), nullable=False),
        sa.Column("entity_key", sa.String(length=200), nullable=False),
        sa.Column("status", reconciliation_status, nullable=False),
        sa.Column("left_value", sa.Text(), nullable=True),
        sa.Column("right_value", sa.Text(), nullable=True),
        sa.Column("difference_value", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["reconciliation_run_id"], ["reconciliation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reconciliation_run_id",
            "entity_table",
            "entity_key",
            name="uq_reconciliation_results_run_entity",
        ),
    )
    op.create_index("ix_reconciliation_results_status", "reconciliation_results", ["status"], unique=False)
    op.create_index(
        "ix_reconciliation_results_entity",
        "reconciliation_results",
        ["entity_table", "entity_key"],
        unique=False,
    )

    op.create_table(
        "review_actions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_table", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("action_type", review_action_type, nullable=False),
        sa.Column("review_status", sa.String(length=30), nullable=False),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("acted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_actions_entity", "review_actions", ["entity_table", "entity_id"], unique=False)
    op.create_index("ix_review_actions_status", "review_actions", ["review_status"], unique=False)
    op.create_index("ix_review_actions_actor", "review_actions", ["actor_email"], unique=False)

    op.create_table(
        "dataset_releases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dataset_name", sa.String(length=120), nullable=False),
        sa.Column("release_version", sa.String(length=60), nullable=False),
        sa.Column("status", dataset_release_status, nullable=False),
        sa.Column("release_notes", sa.Text(), nullable=True),
        sa.Column("manifest_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("manifest_storage_key", sa.String(length=600), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_name", "release_version", name="uq_dataset_releases_dataset_version"),
    )
    op.create_index("ix_dataset_releases_status", "dataset_releases", ["status"], unique=False)
    op.create_index("ix_dataset_releases_published_at", "dataset_releases", ["published_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dataset_releases_published_at", table_name="dataset_releases")
    op.drop_index("ix_dataset_releases_status", table_name="dataset_releases")
    op.drop_table("dataset_releases")

    op.drop_index("ix_review_actions_actor", table_name="review_actions")
    op.drop_index("ix_review_actions_status", table_name="review_actions")
    op.drop_index("ix_review_actions_entity", table_name="review_actions")
    op.drop_table("review_actions")

    op.drop_index("ix_reconciliation_results_entity", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_results_status", table_name="reconciliation_results")
    op.drop_table("reconciliation_results")

    op.drop_index("ix_reconciliation_runs_status", table_name="reconciliation_runs")
    op.drop_table("reconciliation_runs")

    op.drop_index("ix_provenance_links_document_page_row", table_name="provenance_links")
    op.drop_index("ix_provenance_links_target", table_name="provenance_links")
    op.drop_table("provenance_links")

    op.drop_index("ix_department_spending_budget_head", table_name="department_spending")
    op.drop_index("ix_department_spending_basis", table_name="department_spending")
    op.drop_index("ix_department_spending_department_period", table_name="department_spending")
    op.drop_table("department_spending")

    op.drop_index("ix_fiscal_metrics_fiscal_year", table_name="fiscal_metrics")
    op.drop_index("ix_fiscal_metrics_department", table_name="fiscal_metrics")
    op.drop_index("ix_fiscal_metrics_metric_period_basis", table_name="fiscal_metrics")
    op.drop_table("fiscal_metrics")

    op.drop_index("ix_debt_positions_instrument", table_name="debt_positions")
    op.drop_index("ix_debt_positions_as_of_basis", table_name="debt_positions")
    op.drop_table("debt_positions")

    op.drop_index("ix_debt_events_instrument_date", table_name="debt_events")
    op.drop_index("ix_debt_events_basis", table_name="debt_events")
    op.drop_index("ix_debt_events_type_date", table_name="debt_events")
    op.drop_table("debt_events")

    op.drop_index("ix_debt_instruments_active", table_name="debt_instruments")
    op.drop_index("ix_debt_instruments_issuer", table_name="debt_instruments")
    op.drop_index("ix_debt_instruments_maturity_date", table_name="debt_instruments")
    op.drop_table("debt_instruments")

    op.drop_index("ix_budget_heads_department_code", table_name="budget_heads")
    op.drop_index("ix_budget_heads_parent_id", table_name="budget_heads")
    op.drop_table("budget_heads")

    op.drop_index("ix_parser_errors_page_row", table_name="parser_errors")
    op.drop_index("ix_parser_errors_run_level", table_name="parser_errors")
    op.drop_table("parser_errors")

    op.drop_index("ix_parser_runs_parser_name", table_name="parser_runs")
    op.drop_index("ix_parser_runs_document_status", table_name="parser_runs")
    op.drop_table("parser_runs")

    op.drop_index("ix_source_pages_row_locator", table_name="source_pages")
    op.drop_index("ix_source_pages_document_page", table_name="source_pages")
    op.drop_table("source_pages")

    op.drop_index("ix_source_fetch_runs_started_at", table_name="source_fetch_runs")
    op.drop_index("ix_source_fetch_runs_source_status", table_name="source_fetch_runs")
    op.drop_table("source_fetch_runs")

    with op.batch_alter_table("source_documents") as batch_op:
        batch_op.drop_constraint("uq_source_documents_source_checksum", type_="unique")
        batch_op.drop_index("ix_source_documents_review_status")
        batch_op.drop_index("ix_source_documents_source_pub_date")
        batch_op.alter_column(
            "review_status",
            existing_type=sa.String(length=30),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "parser_version",
            existing_type=sa.String(length=60),
            type_=sa.String(length=40),
            nullable=False,
        )
        batch_op.alter_column("storage_key", existing_type=sa.String(length=600), type_=sa.String(length=500))
        batch_op.alter_column("title", existing_type=sa.String(length=500), type_=sa.String(length=300))
        batch_op.alter_column("publisher", existing_type=sa.String(length=200), type_=sa.String(length=120))
        batch_op.alter_column(
            "document_type",
            existing_type=source_document_type,
            type_=sa.String(length=40),
            existing_nullable=False,
        )
        batch_op.drop_column("is_active_version")
        batch_op.drop_column("fetch_etag")
        batch_op.drop_column("storage_bucket")
        batch_op.drop_column("content_length_bytes")
        batch_op.drop_column("fiscal_year_label")
        batch_op.drop_column("effective_date")
        batch_op.drop_column("mime_type")
        batch_op.drop_column("canonical_url")