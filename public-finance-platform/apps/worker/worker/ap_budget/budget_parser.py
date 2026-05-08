"""Parser for Andhra Pradesh budget-volume PDFs.

Each fiscal year publishes multiple volumes (e.g. Volume-I-1, Volume-I-2,
Volume-II). The parser scans every page for tables whose header looks
like a budget head ladder (department / scheme columns + budget estimate /
revised estimate / actuals columns) and emits a
:class:`ParsedBudgetSpending` row per data row.

The extracted shape matches what
:func:`worker.tasks.manual_upload._save_department_spending` consumes
(department_code/name, spending_category, basis_tag, fiscal_year,
period_start/end, amount_inr_crore, unit, provenance,
parser_confidence).

Heuristics — not exhaustive — but conservative: a row is only emitted
when at least one numeric "amount" column parses to a Decimal and a
fiscal-year category can be inferred (BE, RE, actuals).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Iterable

try:
    import pdfplumber
except Exception:  # noqa: BLE001
    pdfplumber = None


@dataclass(frozen=True, slots=True)
class _Provenance:
    page_number: int
    row_number: int | None
    row_label: str | None
    quoted_text: str | None


@dataclass(frozen=True, slots=True)
class ParsedBudgetSpending:
    department_code: str
    department_name: str
    spending_category: str  # 'budget_estimate' | 'revised_estimate' | 'actuals'
    basis_tag: str  # 'budgeted' | 'revised' | 'actual'
    fiscal_year: str  # e.g. '2024-25'
    period_start: date
    period_end: date
    amount_inr_crore: Decimal
    unit: str
    provenance: _Provenance
    parser_confidence: float


_FISCAL_RE = re.compile(r"\b(20\d{2})[\-/](\d{2})\b")
_BE_TOKENS = ("budget estimate", "be", "estimates")
_RE_TOKENS = ("revised estimate", "re")
_AC_TOKENS = ("actuals", "actual", "accounts")


def parse_budget_volume(path: Path, fiscal_year: str) -> list[ParsedBudgetSpending]:
    return parse_budget_bytes(
        path.read_bytes(), source_url=str(path), fiscal_year=fiscal_year
    )


def parse_budget_bytes(
    payload: bytes,
    source_url: str = "",
    fiscal_year: str | None = None,
) -> tuple[list, list[ParsedBudgetSpending]]:
    """Return (fiscal_metrics, department_spending) for a budget volume.

    The first return is reserved for top-level fiscal aggregates (revenue,
    capital, etc.); the parser does not currently emit those — callers
    should treat it as an empty list and consume only the second element.
    """
    if pdfplumber is None:
        return [], []

    fy = fiscal_year or _infer_fiscal_year(source_url)
    if not fy:
        return [], []

    period_start, period_end = _fy_to_period(fy)
    rows: list[ParsedBudgetSpending] = []

    try:
        with pdfplumber.open(BytesIO(payload)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    rows.extend(
                        _table_to_rows(
                            table,
                            page_number=page.page_number,
                            fy=fy,
                            period_start=period_start,
                            period_end=period_end,
                        )
                    )
    except Exception:  # noqa: BLE001
        return [], rows
    return [], rows


# ---------------------------------------------------------------------- #


def _table_to_rows(
    table: list[list[str | None]],
    *,
    page_number: int,
    fy: str,
    period_start: date,
    period_end: date,
) -> Iterable[ParsedBudgetSpending]:
    if not table or len(table) < 2:
        return
    header = [_norm(c) for c in (table[0] or [])]
    if not _looks_like_budget_header(header):
        return

    dept_idx = _find_first(header, ["department", "scheme", "head", "particulars", "description"])
    amount_columns = _find_amount_columns(header)
    if dept_idx is None or not amount_columns:
        return

    for row_idx, raw_row in enumerate(table[1:], start=1):
        if not raw_row:
            continue
        dept_label = _norm_str(raw_row[dept_idx] if dept_idx < len(raw_row) else "")
        if not dept_label or dept_label.isdigit():
            continue
        for idx, category in amount_columns:
            if idx >= len(raw_row):
                continue
            amount = _to_decimal(raw_row[idx])
            if amount is None:
                continue
            yield ParsedBudgetSpending(
                department_code=_slug(dept_label)[:40],
                department_name=dept_label[:300],
                spending_category=category,
                basis_tag=_basis_for_category(category),
                fiscal_year=fy,
                period_start=period_start,
                period_end=period_end,
                amount_inr_crore=amount,
                unit="INR crore",
                provenance=_Provenance(
                    page_number=page_number,
                    row_number=row_idx,
                    row_label=dept_label[:300],
                    quoted_text=" | ".join(_norm_str(c) for c in raw_row)[:500],
                ),
                parser_confidence=0.7,
            )


def _looks_like_budget_header(header: list[str]) -> bool:
    joined = " ".join(header)
    has_dept = any(t in joined for t in ("department", "scheme", "head", "particulars"))
    has_amount = any(t in joined for t in _BE_TOKENS + _RE_TOKENS + _AC_TOKENS)
    return has_dept and has_amount


def _find_amount_columns(header: list[str]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for idx, cell in enumerate(header):
        if any(t in cell for t in _BE_TOKENS):
            out.append((idx, "budget_estimate"))
        elif any(t in cell for t in _RE_TOKENS):
            out.append((idx, "revised_estimate"))
        elif any(t in cell for t in _AC_TOKENS):
            out.append((idx, "actuals"))
    return out


def _find_first(header: list[str], options: list[str]) -> int | None:
    for idx, cell in enumerate(header):
        if any(opt in cell for opt in options):
            return idx
    return None


def _basis_for_category(category: str) -> str:
    return {
        "budget_estimate": "budgeted",
        "revised_estimate": "revised",
        "actuals": "actual",
    }.get(category, "budgeted")


def _norm(value: object) -> str:
    return _norm_str(value).lower()


def _norm_str(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _to_decimal(value: object) -> Decimal | None:
    text = _norm_str(value)
    if not text:
        return None
    cleaned = re.sub(r"[,\s₹]", "", text)
    cleaned = cleaned.replace("Rs", "").strip()
    if cleaned in {"", "-", "."}:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if not cleaned or cleaned in {"-", "."}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _infer_fiscal_year(source_url: str) -> str | None:
    if not source_url:
        return None
    match = _FISCAL_RE.search(source_url)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return None


def _fy_to_period(fy: str) -> tuple[date, date]:
    """'2024-25' -> (2024-04-01, 2025-03-31)."""
    match = re.match(r"(\d{4})[\-/](\d{2})", fy)
    if not match:
        # Fallback to current year if the label is unrecognized.
        from datetime import datetime
        year = datetime.utcnow().year
        return date(year, 4, 1), date(year + 1, 3, 31)
    start_year = int(match.group(1))
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)
