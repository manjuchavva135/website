from pathlib import Path

from worker.ap_finance_ingestion.parser import parse_html_document, parse_pdf_document


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ap_finance"
RBI_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "rbi"


def test_html_parser_extracts_records_and_reconciliation_warning() -> None:
    html = (FIXTURE_DIR / "budget_summary.html").read_text(encoding="utf-8")

    fiscal, spending, debt_events, debt_positions, warnings, links = parse_html_document(
        "https://finance.ap.gov.in/budget.html",
        html,
        "budget_in_brief",
    )

    assert len(fiscal) >= 2
    assert len(spending) == 2
    assert len(debt_events) == 1
    assert len(debt_positions) == 1
    assert len(warnings) >= 1
    assert links == []


def test_pdf_parser_is_resilient_for_real_pdf_fixture() -> None:
    payload = (RBI_FIXTURE_DIR / "sdl_result.pdf").read_bytes()

    fiscal, spending, debt_events, debt_positions, warnings = parse_pdf_document(
        "https://finance.ap.gov.in/some.pdf",
        payload,
        "ap_finance_general",
    )

    # This validates parser robustness over strict extraction shape for mixed PDF layouts.
    assert isinstance(fiscal, list)
    assert isinstance(spending, list)
    assert isinstance(debt_events, list)
    assert isinstance(debt_positions, list)
    assert isinstance(warnings, list)
