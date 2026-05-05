"""ingestion mode

Revision ID: 20260505_0003
Revises: 20260424_0002
Create Date: 2026-05-05

"""

from alembic import op
import sqlalchemy as sa


revision = "20260505_0003"
down_revision = "20260424_0002"
branch_labels = None
depends_on = None

ingestion_mode = sa.Enum(
    "auto_fetch",
    "manual_upload",
    name="ingestion_mode",
    native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table("source_documents") as batch_op:
        # Allow manual uploads that have no original URL
        batch_op.alter_column(
            "source_url",
            existing_type=sa.String(length=1000),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "ingestion_mode",
                ingestion_mode,
                nullable=False,
                server_default="auto_fetch",
            )
        )
        batch_op.add_column(
            sa.Column("uploaded_by_email", sa.String(length=255), nullable=True)
        )
        batch_op.create_index(
            "ix_source_documents_ingestion_mode", ["ingestion_mode"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("source_documents") as batch_op:
        batch_op.drop_index("ix_source_documents_ingestion_mode")
        batch_op.drop_column("uploaded_by_email")
        batch_op.drop_column("ingestion_mode")
        batch_op.alter_column(
            "source_url",
            existing_type=sa.String(length=1000),
            nullable=False,
        )
