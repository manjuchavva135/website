from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from worker.cag_ingestion.models import CAGDocumentType


def classify_cag_document_family(url: str, page_title: str = "", anchor_text: str = "") -> str:
    haystack = " ".join([unquote(urlsplit(url).path), urlsplit(url).query, page_title, anchor_text]).lower()
    normalized = re.sub(r"[-_/]+", " ", haystack)

    if "finance accounts" in normalized and re.search(r"\bvol\s*(i|1)\b", normalized):
        return CAGDocumentType.finance_accounts_vol_i
    if "finance accounts" in normalized and re.search(r"\bvol\s*(ii|2)\b", normalized):
        return CAGDocumentType.finance_accounts_vol_ii
    if "accounts at a glance" in normalized:
        return CAGDocumentType.accounts_at_a_glance
    if "appropriation accounts" in normalized:
        return CAGDocumentType.appropriation_accounts
    if "monthly key indicators" in normalized or "mki" in normalized:
        return CAGDocumentType.monthly_key_indicators
    return CAGDocumentType.cag_general
