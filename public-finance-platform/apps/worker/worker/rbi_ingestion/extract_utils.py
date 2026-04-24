from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal


DATE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y"]


def parse_date(value: str) -> datetime.date | None:
    candidate = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(value: str) -> Decimal | None:
    normalized = value.replace(",", "").strip()
    if not normalized:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", normalized)
    if not match:
        return None
    return Decimal(match.group(0))


def compact_whitespace(value: str) -> str:
    return " ".join(value.split())
