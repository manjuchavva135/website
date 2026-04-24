from pathlib import Path

from worker.cag_ingestion.monthly_parser import parse_cag_monthly_key_indicators


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cag"


def test_cag_mki_parser_extracts_monthly_provisional_series() -> None:
    payload = (FIXTURE_DIR / "monthly_key_indicators.pdf").read_bytes()

    result = parse_cag_monthly_key_indicators(
        payload=payload,
        source_url="https://cag.gov.in/reports/mki-april-2025.pdf",
        page_title="Monthly Key Indicators",
    )

    assert result.document_family == "monthly_key_indicators"
    assert result.fiscal_metrics
    assert all(row.basis_tag == "monthly_actual_provisional" for row in result.fiscal_metrics)
    assert all(row.metric_group == "monthly_key_indicators" for row in result.fiscal_metrics)
    assert "contains_provisional_or_awaited_disclosure" in result.parser_notes


def test_cag_mki_parser_reports_missing_series_without_failure() -> None:
    payload = b"Monthly Key Indicators\nNo table rows available"

    result = parse_cag_monthly_key_indicators(
        payload=payload,
        source_url="https://cag.gov.in/reports/mki-empty.pdf",
    )

    assert result is not None
    assert "missing_monthly_key_indicator_series" in result.missing_or_awaited_fields
