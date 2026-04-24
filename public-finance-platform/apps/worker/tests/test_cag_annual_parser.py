from pathlib import Path

from worker.cag_ingestion.annual_parser import parse_cag_annual_accounts


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cag"


def test_cag_annual_parser_extracts_core_metrics_spending_and_debt_with_provenance() -> None:
    payload = (FIXTURE_DIR / "finance_accounts_vol_i.pdf").read_bytes()

    result = parse_cag_annual_accounts(
        payload=payload,
        source_url="https://cag.gov.in/reports/finance-accounts-vol-i-2025.pdf",
        page_title="Finance Accounts Vol I",
    )

    assert result.document_family == "finance_accounts_vol_i"
    assert result.fiscal_metrics
    assert result.debt_positions
    assert result.department_spending

    assert all(row.basis_tag == "audited_actual" for row in result.fiscal_metrics)
    assert all(row.basis_tag == "audited_actual" for row in result.debt_positions)
    assert all(row.basis_tag == "audited_actual" for row in result.department_spending)

    assert any(item.metric_group == "receipts" for item in result.fiscal_metrics)
    assert any(item.metric_group == "expenditure" for item in result.fiscal_metrics)
    assert any(item.metric_group == "deficit" for item in result.fiscal_metrics)
    assert any("savings" in row.spending_category for row in result.department_spending)

    assert all(item.provenance.page_number > 0 for item in result.fiscal_metrics)
    assert all(item.provenance.page_number > 0 for item in result.debt_positions)
    assert all(item.provenance.page_number > 0 for item in result.department_spending)

    assert "contains_authoritative_precedence_note" in result.parser_notes
    assert "contains_provisional_or_awaited_disclosure" in result.parser_notes


def test_cag_annual_parser_handles_missing_fields_without_crashing() -> None:
    payload = b"Finance Accounts Vol I 2025-26\nItem | Amount\nUnrelated Row | 50"

    result = parse_cag_annual_accounts(
        payload=payload,
        source_url="https://cag.gov.in/reports/finance-accounts-vol-i-2025.pdf",
    )

    assert result is not None
    assert "missing_receipts" in result.missing_or_awaited_fields
    assert "missing_public_debt" in result.missing_or_awaited_fields
