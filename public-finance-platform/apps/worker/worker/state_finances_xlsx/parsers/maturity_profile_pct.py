"""RBI Statement 24 — Maturity Profile as per cent of Total.

Same layout as Statement 23 but values are percentages of the state's total
outstanding SDL stock.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import (
    fiscal_period,
    is_column_number_row,
    normalize_text,
    open_first_sheet,
    to_decimal,
)
from worker.state_finances_xlsx.records import FiscalMetricRow, XlsxProvenance
from worker.state_finances_xlsx.state_codes import normalize_state

_FY_BUCKET_RE = re.compile(r"(\d{4})\s*-\s*(\d{4})")
_AS_OF_RE = re.compile(r"as on march 31,\s*(\d{4})", re.IGNORECASE)


def _bucket_to_fy(label: str) -> str | None:
    m = _FY_BUCKET_RE.search(label)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)[-2:]}"


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    ws = open_first_sheet(str(path))
    rows = list(ws.iter_rows(values_only=True))

    as_of_year: int | None = None
    for r in rows[:6]:
        for cell in r:
            m = _AS_OF_RE.search(normalize_text(cell))
            if m:
                as_of_year = int(m.group(1))
                break
        if as_of_year:
            break

    from worker.state_finances_xlsx.common import is_state_header_cell

    header_idx: int | None = None
    for i, row in enumerate(rows[:14]):
        if any(is_state_header_cell(cell) for cell in row):
            header_idx = i
            break
    if header_idx is None:
        return

    header = rows[header_idx]
    columns: list[tuple[int, str, str]] = []
    for col_idx in range(3, len(header) + 1):
        label = normalize_text(header[col_idx - 1])
        if not label:
            continue
        fy = _bucket_to_fy(label)
        if fy is None:
            continue
        columns.append((col_idx, fy, label))

    sheet_name = ws.title
    for row_idx, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        if is_column_number_row(row):
            continue
        state_cell = row[1] if len(row) > 1 else None
        state_code = normalize_state(state_cell)
        if state_code is None:
            continue
        for col_idx, fy, raw_label in columns:
            value = to_decimal(row[col_idx - 1] if col_idx - 1 < len(row) else None)
            if value is None:
                continue
            period_start, period_end = fiscal_period(fy)
            yield FiscalMetricRow(
                state_code=state_code,
                metric_code="sdl_maturity_pct_total",
                metric_name="SDL Maturity Bucket (% of Total Outstanding)",
                metric_group="debt_pipeline",
                basis_tag="scheduled",
                fiscal_year=fy,
                period_start=period_start,
                period_end=period_end,
                value=value,
                unit="percent",
                unit_scale="percent",
                notes=f"As outstanding on March 31, {as_of_year}" if as_of_year else None,
                provenance=XlsxProvenance(
                    sheet_name=sheet_name,
                    row_number=row_idx,
                    column_index=col_idx,
                    column_label=raw_label,
                    row_label=str(state_cell),
                ),
            )
