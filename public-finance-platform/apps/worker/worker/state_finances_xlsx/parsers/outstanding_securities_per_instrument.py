"""Per-instrument outstanding SDL list (legacy .XLS file from RBI).

Each row is one State Government Security: ISIN, state, nomenclature
(e.g. '6.39% ANDHRA SDL 2026' — coupon + issuer + maturity year), issue date,
maturity date, outstanding stock in ₹ Crore.

Coupon is parsed from the leading 'X.XX%' in the nomenclature; instrument
type is fixed at 'state_development_loan'.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import xlrd

from worker.state_finances_xlsx.records import DebtInstrumentRow, XlsxProvenance
from worker.state_finances_xlsx.state_codes import normalize_state

_COUPON_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%")
_AS_OF_RE = re.compile(r"as on\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})", re.IGNORECASE)


def _excel_serial_to_date(value: object) -> date | None:
    """Excel uses 1900-based serials with the leap-year quirk."""
    if value is None or value == "":
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    base = datetime(1899, 12, 30)
    return (base + timedelta(days=n)).date()


def _parse_coupon(nomenclature: str) -> Decimal | None:
    m = _COUPON_RE.match(nomenclature)
    if not m:
        return None
    try:
        return Decimal(m.group(1))
    except Exception:
        return None


def _detect_as_of(ws: xlrd.sheet.Sheet) -> date:
    for r in range(min(ws.nrows, 5)):
        for c in range(ws.ncols):
            val = ws.cell_value(r, c)
            if not isinstance(val, str):
                continue
            m = _AS_OF_RE.search(val)
            if m:
                try:
                    return datetime.strptime(m.group(1).replace(",", " "), "%B %d  %Y").date()
                except ValueError:
                    pass
                try:
                    return datetime.strptime(m.group(1), "%B %d, %Y").date()
                except ValueError:
                    pass
    return date.today()


def parse(path: Path) -> Iterable[DebtInstrumentRow]:
    book = xlrd.open_workbook(str(path))
    ws = book.sheet_by_index(0)
    sheet_name = ws.name
    as_of = _detect_as_of(ws)

    # Locate header row by scanning for 'ISIN'
    header_row_idx = -1
    for r in range(min(ws.nrows, 10)):
        for c in range(ws.ncols):
            val = ws.cell_value(r, c)
            if isinstance(val, str) and val.strip().upper() == "ISIN":
                header_row_idx = r
                break
        if header_row_idx >= 0:
            break
    if header_row_idx < 0:
        return

    # Map header labels to columns.
    header = [str(ws.cell_value(header_row_idx, c)).strip() for c in range(ws.ncols)]
    col = {h.lower(): i for i, h in enumerate(header)}
    isin_col = col.get("isin")
    state_col = col.get("state government")
    nom_col = col.get("nomenclature")
    issue_col = col.get("date of issue")
    mat_col = col.get("date of maturity")
    out_col: int | None = None
    for h, i in col.items():
        if h.startswith("outstanding stock"):
            out_col = i
            break
    if None in (isin_col, state_col, nom_col, issue_col, mat_col, out_col):
        return

    for r in range(header_row_idx + 1, ws.nrows):
        isin = str(ws.cell_value(r, isin_col)).strip()
        if not isin or isin.lower() == "isin":
            continue
        state_raw = ws.cell_value(r, state_col)
        state_code = normalize_state(state_raw) or normalize_state(str(state_raw))
        if state_code is None:
            continue
        nomenclature = str(ws.cell_value(r, nom_col)).strip()
        if not nomenclature:
            continue
        try:
            outstanding = Decimal(str(ws.cell_value(r, out_col)))
        except Exception:
            continue
        yield DebtInstrumentRow(
            issuer_state_code=state_code,
            issuer_name=str(state_raw).title(),
            instrument_code=isin,
            instrument_name=nomenclature,
            instrument_type="state_development_loan",
            coupon_rate=_parse_coupon(nomenclature),
            issue_date=_excel_serial_to_date(ws.cell_value(r, issue_col)),
            maturity_date=_excel_serial_to_date(ws.cell_value(r, mat_col)),
            outstanding_principal=outstanding,
            as_of_date=as_of,
            provenance=XlsxProvenance(
                sheet_name=sheet_name,
                row_number=r + 1,
                column_index=out_col + 1,
                column_label=header[out_col],
                row_label=isin,
            ),
        )
