from decimal import Decimal

from worker.ap_finance_ingestion.basis_rules import map_basis_tag
from worker.ap_finance_ingestion.classifier import classify_ap_document_family
from worker.ap_finance_ingestion.units import detect_unit_label, normalize_to_crore


def test_classifier_maps_known_families() -> None:
    assert classify_ap_document_family("https://finance.ap.gov.in/docs/Annual_Financial_Statement_2025.pdf") == "annual_financial_statement"
    assert classify_ap_document_family("https://finance.ap.gov.in/frbm/Q1_review.pdf", anchor_text="FRBM quarterly review") == "frbm_quarterly"


def test_basis_and_unit_normalization() -> None:
    assert map_basis_tag("Budget in Brief BE 2025-26", "budget_in_brief") == "budget_estimate"
    assert map_basis_tag("FRBM Q2 review", "frbm_quarterly") == "quarter_actual"

    assert detect_unit_label("All values in lakh rupees") == "INR lakh"
    assert normalize_to_crore(Decimal("250"), "INR lakh") == Decimal("2.5000")
    assert normalize_to_crore(Decimal("12.5"), "INR crore") == Decimal("12.5")
