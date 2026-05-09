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
    r"as\s+on\s+("
    r"\d{1,2}[-/\s][A-Za-z]+[-/\s]\d{2,4}"     # 06-May-2026 / 06 May 2026
    r"|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"          # 06/05/2026
    r"|[A-Za-z]+\s+\d{1,2},\s*\d{4}"           # May 06, 2026
    r")",
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
    sticky_cols: dict[str, int] = {}

    try:
        with pdfplumber.open(BytesIO(payload)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if as_of_default is None:
                    as_of_default = _find_as_of_date(page_text)

                for table in page.extract_tables() or []:
                    if not table:
                        continue
                    header_idx = _find_header_row(table)
                    if header_idx is not None:
                        header = [_norm(c) for c in (table[header_idx] or [])]
                        cols = _map_columns(header)
                        if cols:
                            sticky_cols = cols
                        data_start = header_idx + 1
                    else:
                        cols = sticky_cols
                        data_start = 0
                    if not cols:
                        continue
                    for raw_row in table[data_start:]:
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


def _find_header_row(table: list[list[str | None]]) -> int | None:
    """Return the index of the row that looks like the column header.

    Heuristic: a header has *multiple* short label cells. A leading title row
    (e.g. "List of State Government Securities outstanding as on ...") is a
    single long string in one cell. We prefer rows containing 'isin' explicitly.
    """
    for idx, row in enumerate(table[:6]):
        cells = [_norm(c) for c in (row or [])]
        non_empty = [c for c in cells if c]
        if any("isin" in c for c in non_empty):
            return idx
    # Fallback: row with >=3 short label cells where at least one mentions
    # 'state' and another mentions 'outstanding'.
    for idx, row in enumerate(table[:6]):
        cells = [_norm(c) for c in (row or [])]
        non_empty = [c for c in cells if c and len(c) <= 60]
        if len(non_empty) >= 3 and any("state" in c for c in non_empty) and any("outstanding" in c for c in non_empty):
            return idx
    return None


def _map_columns(header: list[str]) -> dict[str, int]:
    aliases = {
        "state": ["state government", "state", "issuer"],
        "isin": ["isin"],
        "name": ["nomenclature", "security", "issue", "description", "name"],
        "coupon": ["coupon", "rate of interest", "interest rate"],
        "issue_date": ["date of issue", "issue date"],
        "maturity": ["date of maturity", "maturity date", "maturity"],
        "outstanding": [
            "outstanding stock",
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
    coupon = _to_decimal(cell("coupon"))
    if coupon is None:
        # Coupon may be embedded in the nomenclature: "6.39% ANDHRA SDL 2026".
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s*%", name)
        if m:
            coupon = _to_decimal(m.group(1))
    return OutstandingPosition(
        state="Andhra Pradesh",
        instrument_code=code,
        instrument_name=name,
        maturity_date=parse_date(cell("maturity")),
        coupon_rate=coupon,
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
