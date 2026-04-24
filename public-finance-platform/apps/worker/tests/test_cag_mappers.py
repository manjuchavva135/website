from pathlib import Path

from worker.cag_ingestion.annual_parser import parse_cag_annual_accounts
from worker.cag_ingestion.mappers import (
    map_to_debt_positions_fields,
    map_to_department_spending_fields,
    map_to_fiscal_metrics_fields,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cag"


def test_cag_mapper_fields_match_canonical_targets() -> None:
    payload = (FIXTURE_DIR / "finance_accounts_vol_i.pdf").read_bytes()
    result = parse_cag_annual_accounts(
        payload=payload,
        source_url="https://cag.gov.in/reports/finance-accounts-vol-i-2025.pdf",
    )

    fiscal_row = map_to_fiscal_metrics_fields(result.fiscal_metrics[0])
    debt_row = map_to_debt_positions_fields(result.debt_positions[0])
    spending_row = map_to_department_spending_fields(result.department_spending[0])

    assert fiscal_row["target_table"] == "fiscal_metrics"
    assert {"metric_code", "metric_group", "basis_tag", "period_start", "period_end", "value"}.issubset(fiscal_row.keys())

    assert debt_row["target_table"] == "debt_positions"
    assert {"instrument_code", "as_of_date", "basis_tag", "outstanding_principal"}.issubset(debt_row.keys())

    assert spending_row["target_table"] == "department_spending"
    assert {"department_code", "spending_category", "basis_tag", "period_start", "period_end", "amount"}.issubset(spending_row.keys())
