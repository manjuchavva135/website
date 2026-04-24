"""initial schema

Revision ID: 20260424_0001
Revises: 
Create Date: 2026-04-24

"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("publisher", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_source_documents_source_name", "source_documents", ["source_name"], unique=False)
    op.create_index("ix_source_documents_checksum_sha256", "source_documents", ["checksum_sha256"], unique=False)

    op.create_table(
        "source_rows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("row_label", sa.String(length=300), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_rows_checksum_sha256", "source_rows", ["checksum_sha256"], unique=False)

    op.create_table(
        "metric_series",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("metric_group", sa.String(length=60), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_metric_series_metric_group", "metric_series", ["metric_group"], unique=False)
    op.create_index("ix_metric_series_slug", "metric_series", ["slug"], unique=False)

    op.create_table(
        "metric_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_label", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("basis", sa.String(length=40), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("source_row_id", sa.Integer(), nullable=True),
        sa.Column("provenance_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["metric_series.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"]),
        sa.ForeignKeyConstraint(["source_row_id"], ["source_rows.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "series_id",
            "period_start",
            "period_end",
            "basis",
            name="uq_metric_observation_series_period_basis",
        ),
    )
    op.create_index("ix_metric_observations_basis", "metric_observations", ["basis"], unique=False)
    op.create_index("ix_metric_observations_series_id", "metric_observations", ["series_id"], unique=False)
    op.create_index(
        "ix_metric_observations_source_document_id", "metric_observations", ["source_document_id"], unique=False
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_runs_source_name", "ingestion_runs", ["source_name"], unique=False)
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"], unique=False)

    op.create_table(
        "changelog_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_changelog_entries_version", "changelog_entries", ["version"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_changelog_entries_version", table_name="changelog_entries")
    op.drop_table("changelog_entries")

    op.drop_index("ix_ingestion_runs_status", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_source_name", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index("ix_metric_observations_source_document_id", table_name="metric_observations")
    op.drop_index("ix_metric_observations_series_id", table_name="metric_observations")
    op.drop_index("ix_metric_observations_basis", table_name="metric_observations")
    op.drop_table("metric_observations")

    op.drop_index("ix_metric_series_slug", table_name="metric_series")
    op.drop_index("ix_metric_series_metric_group", table_name="metric_series")
    op.drop_table("metric_series")

    op.drop_index("ix_source_rows_checksum_sha256", table_name="source_rows")
    op.drop_table("source_rows")

    op.drop_index("ix_source_documents_checksum_sha256", table_name="source_documents")
    op.drop_index("ix_source_documents_source_name", table_name="source_documents")
    op.drop_table("source_documents")
