"""state dimension on fiscal facts

Adds the state_code dimension that lets the same metric carry rows for every
Indian state, enabling AP-vs-peers comparison without splitting tables. Also
adds unit_scale on fiscal_metrics so ratio-typed RBI statements (debt/GSDP,
maturity %, education %) can sit alongside ₹-crore values without ambiguity.

Revision ID: 20260512_0004
Revises: 20260505_0003
Create Date: 2026-05-12

"""

from alembic import op
import sqlalchemy as sa


revision = "20260512_0004"
down_revision = "20260505_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # fiscal_metrics: state_code + unit_scale, recompose unique key.     #
    # ------------------------------------------------------------------ #
    with op.batch_alter_table("fiscal_metrics") as batch_op:
        batch_op.add_column(
            sa.Column("state_code", sa.String(length=8), nullable=True, server_default="AP")
        )
        batch_op.add_column(
            sa.Column(
                "unit_scale",
                sa.String(length=20),
                nullable=True,
                server_default="inr_crore",
            )
        )

    op.execute("UPDATE fiscal_metrics SET state_code = 'AP' WHERE state_code IS NULL")
    op.execute("UPDATE fiscal_metrics SET unit_scale = 'inr_crore' WHERE unit_scale IS NULL")

    with op.batch_alter_table("fiscal_metrics") as batch_op:
        batch_op.alter_column("state_code", existing_type=sa.String(length=8), nullable=False)
        batch_op.alter_column("unit_scale", existing_type=sa.String(length=20), nullable=False)
        batch_op.drop_constraint("uq_fiscal_metrics_natural_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_fiscal_metrics_natural_key",
            ["state_code", "metric_code", "period_start", "period_end", "basis_tag", "department_code"],
        )
        batch_op.create_index(
            "ix_fiscal_metrics_state_metric_year",
            ["state_code", "metric_code", "fiscal_year"],
            unique=False,
        )

    # ------------------------------------------------------------------ #
    # metric_series: same state dimension on the lighter series table.   #
    # ------------------------------------------------------------------ #
    with op.batch_alter_table("metric_series") as batch_op:
        batch_op.add_column(
            sa.Column("state_code", sa.String(length=8), nullable=True, server_default="AP")
        )

    op.execute("UPDATE metric_series SET state_code = 'AP' WHERE state_code IS NULL")

    with op.batch_alter_table("metric_series") as batch_op:
        batch_op.alter_column("state_code", existing_type=sa.String(length=8), nullable=False)
        batch_op.create_index("ix_metric_series_state_code", ["state_code"], unique=False)

    # ------------------------------------------------------------------ #
    # debt_instruments: derived issuer_state_code so peer queries don't  #
    # have to LIKE-match on free-text issuer_name.                       #
    # ------------------------------------------------------------------ #
    with op.batch_alter_table("debt_instruments") as batch_op:
        batch_op.add_column(
            sa.Column("issuer_state_code", sa.String(length=8), nullable=True)
        )

    op.execute(
        "UPDATE debt_instruments SET issuer_state_code = 'AP' "
        "WHERE LOWER(issuer_name) LIKE '%andhra pradesh%' "
        "   OR LOWER(issuer_name) LIKE '%government of ap%'"
    )

    with op.batch_alter_table("debt_instruments") as batch_op:
        batch_op.create_index(
            "ix_debt_instruments_issuer_state", ["issuer_state_code"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("debt_instruments") as batch_op:
        batch_op.drop_index("ix_debt_instruments_issuer_state")
        batch_op.drop_column("issuer_state_code")

    with op.batch_alter_table("metric_series") as batch_op:
        batch_op.drop_index("ix_metric_series_state_code")
        batch_op.drop_column("state_code")

    with op.batch_alter_table("fiscal_metrics") as batch_op:
        batch_op.drop_index("ix_fiscal_metrics_state_metric_year")
        batch_op.drop_constraint("uq_fiscal_metrics_natural_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_fiscal_metrics_natural_key",
            ["metric_code", "period_start", "period_end", "basis_tag", "department_code"],
        )
        batch_op.drop_column("unit_scale")
        batch_op.drop_column("state_code")
