"""Parser for the RBI 'Outstanding State Government Securities' PDF.

Filters to Andhra Pradesh and emits authoritative DebtPosition records.
This source takes precedence over computed positions during reconciliation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from worker.rbi_ingestion.extract_utils import compact_whitespace, parse_date

try:
    import pdfplumber
except Exception:  # noqa: BLE001
    pdfplumber = None


_AP_RE = re.compile(r"\bandhra\s+pradesh\b", re.IGNORECASE)
_AS_OF_RE = re.compile(
    r"as\s+on\s+(\d{1,2}[-/\s][A-Za-z]+[-/\s]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class OutstandingPosition:
    state: str
    instrument_code: str
    instrument_name: str
    maturity_date: date | None
    coupon_rate: Decimal | None
    outstanding_principal: Decimal
    as_of_date: date | None
    source_url: str


def parse_outstanding_securities(path: Path) -> list[OutstandingPosition]:
    """Parse the OUTSTANDINGSGSDATA PDF on disk and return AP positions."""
    return parse_outstanding_securities_bytes(path.read_bytes(), source_url=str(path))


def parse_outstanding_securities_bytes(
    payload: bytes, source_url: str
) -> list[OutstandingPosition]:
    if pdfplumber is None:
        return []

    positions: list[OutstandingPosition] = []
    as_of_default: date | None = None

    try:
        with pdfplumber.open(BytesIO(payload)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if as_of_default is None:
                    as_of_default = _find_as_of_date(page_text)

                for table in page.extract_tables() or []:
                    if not table:
                        continue
                    header = [_norm(c) for c in (table[0] or [])]
                    cols = _map_columns(header)
                    if not cols:
                        continue
                    for raw_row in table[1:]:
                        if not raw_row:
                            continue
                        if not _row_is_ap(raw_row, cols.get("state")):
                            continue
                        pos = _row_to_position(raw_row, cols, source_url, as_of_default)
                        if pos is not None:
                            positions.append(pos)
    except Exception:  # noqa: BLE001
        return positions
    return positions


def _norm(value: object) -> str:
    return compact_whitespace(str(value or "")).lower()


def _map_columns(header: list[str]) -> dict[str, int]:
    aliases = {
        "state": ["state", "state government", "issuer"],
        "isin": ["isin"],
        "name": ["security", "issue", "description", "name"],
        "coupon": ["coupon", "rate of interest", "interest rate"],
        "maturity": ["maturity date", "maturity"],
        "outstanding": [
            "outstanding amount",
            "outstanding (rs crore)",
            "outstanding",
            "amount outstanding",
        ],
    }
    out: dict[str, int] = {}
    for key, options in aliases.items():
        for idx, cell in enumerate(header):
            if any(opt in cell for opt in options):
                out[key] = idx
                break
    return out


def _row_is_ap(raw_row: list[str | None], state_idx: int | None) -> bool:
    if state_idx is not None and state_idx < len(raw_row):
        if _AP_RE.search(str(raw_row[state_idx] or "")):
            return True
    return any(_AP_RE.search(str(c or "")) for c in raw_row)


def _row_to_position(
    raw_row: list[str | None],
    cols: dict[str, int],
    source_url: str,
    as_of_default: date | None,
) -> OutstandingPosition | None:
    def cell(key: str) -> str:
        idx = cols.get(key)
        if idx is None or idx >= len(raw_row):
            return ""
        return compact_whitespace(str(raw_row[idx] or ""))

    outstanding = _to_decimal(cell("outstanding"))
    if outstanding is None:
        return None

    name = cell("name") or "Andhra Pradesh SDL"
    isin = cell("isin")
    code = isin or _slug(name)
    return OutstandingPosition(
        state="Andhra Pradesh",
        instrument_code=code,
        instrument_name=name,
        maturity_date=parse_date(cell("maturity")),
        coupon_rate=_to_decimal(cell("coupon")),
        outstanding_principal=outstanding,
        as_of_date=as_of_default,
        source_url=source_url,
    )


def _slug(name: str) -> str:
    cleaned = re.sub(r"\s+", "_", name.strip().lower())
    return f"ap_outstanding_{cleaned[:60]}"


def _to_decimal(text: str) -> Decimal | None:
    if not text:
        return None
    cleaned = text.replace(",", "").replace("₹", "").replace("Rs", "").strip()
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if not cleaned or cleaned in {"-", "."}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _find_as_of_date(text: str) -> date | None:
    match = _AS_OF_RE.search(text)
    if not match:
        return None
    return parse_date(match.group(1))
