from sqlalchemy.orm import configure_mappers

from app.db.session import Base
from app.models import BasisTag


def test_canonical_tables_registered() -> None:
    configure_mappers()

    expected_tables = {
        "source_documents",
        "source_fetch_runs",
        "source_pages",
        "parser_runs",
        "parser_errors",
        "budget_heads",
        "debt_instruments",
        "debt_events",
        "debt_positions",
        "fiscal_metrics",
        "department_spending",
        "provenance_links",
        "reconciliation_runs",
        "reconciliation_results",
        "review_actions",
        "dataset_releases",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_basis_tag_values_match_contract() -> None:
    assert [tag.value for tag in BasisTag] == [
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
    ]