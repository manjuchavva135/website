from __future__ import annotations

from worker.cag_ingestion.models import CAGDocumentType


def assign_basis_tag(document_family: str) -> str:
    if document_family == CAGDocumentType.monthly_key_indicators:
        return "monthly_actual_provisional"
    if document_family in {
        CAGDocumentType.finance_accounts_vol_i,
        CAGDocumentType.finance_accounts_vol_ii,
        CAGDocumentType.accounts_at_a_glance,
        CAGDocumentType.appropriation_accounts,
    }:
        return "audited_actual"
    return "actual"
