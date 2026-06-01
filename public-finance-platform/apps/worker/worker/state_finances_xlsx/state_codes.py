"""RBI state name → 2-letter code map.

RBI tables list states with a numbered prefix like '1. Andhra Pradesh'.
``normalize_state(raw)`` strips the prefix, lowercases, then maps to the
canonical code. Returns ``None`` for header/total/footnote rows so the
caller can skip them silently.
"""

from __future__ import annotations

import re
from typing import Final

# Order matches the typical RBI table ordering for sanity-checks during ingest.
_NAME_TO_CODE: Final[dict[str, str]] = {
    "andhra pradesh": "AP",
    "arunachal pradesh": "AR",
    "assam": "AS",
    "bihar": "BR",
    "chhattisgarh": "CG",
    "goa": "GA",
    "gujarat": "GJ",
    "haryana": "HR",
    "himachal pradesh": "HP",
    "himachal": "HP",
    "jammu and kashmir": "JK",
    "jammu & kashmir": "JK",
    "jammu and kashmir ut": "JK",
    "jharkhand": "JH",
    "karnataka": "KA",
    "kerala": "KL",
    "madhya pradesh": "MP",
    "maharashtra": "MH",
    "manipur": "MN",
    "meghalaya": "ML",
    "mizoram": "MZ",
    "nagaland": "NL",
    "odisha": "OD",
    "orissa": "OD",
    "punjab": "PB",
    "rajasthan": "RJ",
    "sikkim": "SK",
    "tamil nadu": "TN",
    "tamilnadu": "TN",
    "telangana": "TS",
    "tripura": "TR",
    "uttar pradesh": "UP",
    "uttarakhand": "UK",
    "uttaranchal": "UK",
    "west bengal": "WB",
    "delhi": "DL",
    "nct of delhi": "DL",
    "puducherry": "PY",
    "pondicherry": "PY",
    # Aggregates that appear as the last few rows of most RBI tables.
    "all states": "ALL",
    "all states and uts": "ALL",
    "all states/uts": "ALL",
    "all states / uts": "ALL",
    "all states & uts": "ALL",
    "all states/uts with legislature": "ALL",
    "non-special category": "NSC",
    "non special category": "NSC",
    "special category": "SC",
}

_PREFIX_RE = re.compile(r"^\s*\d+\s*[.)]\s*")
_PUNCT_RE = re.compile(r"[*†‡§¶#]+")


def normalize_state(raw: object) -> str | None:
    """Return the state code for an RBI row label, or None to skip."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = _PREFIX_RE.sub("", text)
    text = _PUNCT_RE.sub("", text)
    text = text.replace("–", "-").strip().lower()
    if text in _NAME_TO_CODE:
        return _NAME_TO_CODE[text]
    # Strip parenthetical suffixes like "Andhra Pradesh (residual)"
    if "(" in text:
        head = text.split("(", 1)[0].strip()
        if head in _NAME_TO_CODE:
            return _NAME_TO_CODE[head]
    return None
