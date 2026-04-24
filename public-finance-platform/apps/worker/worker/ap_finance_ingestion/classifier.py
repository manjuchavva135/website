from __future__ import annotations

from urllib.parse import unquote, urlsplit


def classify_ap_document_family(url: str, page_title: str = "", anchor_text: str = "") -> str:
    haystack = " ".join([unquote(urlsplit(url).path), urlsplit(url).query, page_title, anchor_text]).lower()

    if "annual financial statement" in haystack or "annual_financial_statement" in haystack or "afs" in haystack:
        return "annual_financial_statement"
    if "demands for grants" in haystack:
        return "demands_for_grants"
    if "detailed estimates" in haystack or "revenue receipts" in haystack:
        return "detailed_estimates_receipts"
    if "public account" in haystack:
        return "public_account"
    if "budget in brief" in haystack:
        return "budget_in_brief"
    if "frbm" in haystack and any(token in haystack for token in {"annual", "fiscal policy"}):
        return "frbm_annual"
    if "frbm" in haystack and any(token in haystack for token in {"quarter", "q1", "q2", "q3", "q4"}):
        return "frbm_quarterly"
    return "ap_finance_general"
