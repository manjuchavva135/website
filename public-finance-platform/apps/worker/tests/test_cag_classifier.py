from worker.cag_ingestion.classifier import classify_cag_document_family
from worker.cag_ingestion.models import CAGDocumentType


def test_cag_document_family_classifier() -> None:
    assert (
        classify_cag_document_family("https://cag.gov.in/reports/finance-accounts-vol-i-2025.pdf")
        == CAGDocumentType.finance_accounts_vol_i
    )
    assert (
        classify_cag_document_family("https://cag.gov.in/reports/appropriation-accounts-2025.pdf")
        == CAGDocumentType.appropriation_accounts
    )
    assert (
        classify_cag_document_family("https://cag.gov.in/reports/mki-april-2025.pdf", anchor_text="Monthly Key Indicators")
        == CAGDocumentType.monthly_key_indicators
    )
