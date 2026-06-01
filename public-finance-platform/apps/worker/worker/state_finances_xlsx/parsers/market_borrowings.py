"""RBI Statement 21 — Market Borrowings of State Governments (₹ Crore).

Header row carries fiscal year labels with empty merged cells; the row below
splits each FY into 'Gross Amount Raised' and 'Repayments' sub-columns.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import (
    fiscal_period,
    fiscal_year_from_label,
    is_column_number_row,
    normalize_text,
    open_first_sheet,
    to_decimal,
)
from worker.state_finances_xlsx.records import FiscalMetricRow, XlsxProvenance
from worker.state_finances_xlsx.state_codes import normalize_state

_SUB_TO_METRIC: dict[str, tuple[str, str]] = {
    "gross amount raised": ("market_borrowings_gross_raised", "Market Borrowings — Gross Amount Raised"),
    "repayments": ("market_borrowings_repayments", "Market Borrowings — Repayments"),
}


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    ws = open_first_sheet(str(path))
    rows = list(ws.iter_rows(values_only=True))

    # Find the FY header row: first row whose first non-empty label is 'State/UTs' or 'State/UT'.
    fy_row_idx: int | None = None
    for i, row in enumerate(rows[:10]):
        for cell in row:
            text = normalize_text(cell).lower()
            if text in {"state/ut", "state/uts"}:
                fy_row_idx = i
                break
        if fy_row_idx is not None:
            break
    if fy_row_idx is None:
        return
    sub_row_idx = fy_row_idx + 1

    fy_row = rows[fy_row_idx]
    sub_row = rows[sub_row_idx]

    # Build (col_idx, fy, basis, metric_code, metric_name, raw_label) for each data column.
    # FY labels appear once and are visually merged; openpyxl returns the value only on
    # the first cell of the merge — so we forward-fill.
    last_fy_label: str | None = None
    columns: list[tuple[int, str, str, str, str, str]] = []
    for col_idx in range(3, len(fy_row) + 1):
        fy_cell = normalize_text(fy_row[col_idx - 1])
        if fy_cell:
            last_fy_label = fy_cell
        if not last_fy_label:
            continue
        sub_label = normalize_text(sub_row[col_idx - 1] if col_idx - 1 < len(sub_row) else None)
        if not sub_label:
            continue
        slug = _SUB_TO_METRIC.get(sub_label.lower())
        if slug is None:
            continue
        fy = fiscal_year_from_label(last_fy_label)
        if not fy:
            continue
        lower_fy = last_fy_label.lower()
        if "(be)" in lower_fy or " be" in lower_fy or "*" in last_fy_label:
            basis = "budget_estimate"
        elif "(re)" in lower_fy or " re" in lower_fy:
            basis = "revised_estimate"
        else:
            basis = "audited_actual"
        columns.append((col_idx, fy, basis, slug[0], slug[1], f"{last_fy_label} | {sub_label}"))

    sheet_name = ws.title
    for row_idx, row in enumerate(rows[sub_row_idx + 1 :], start=sub_row_idx + 2):
        if is_column_number_row(row):
            continue
        state_cell = row[1] if len(row) > 1 else None
        state_code = normalize_state(state_cell)
        if state_code is None:
            continue
        for col_idx, fy, basis, metric_code, metric_name, raw_label in columns:
            value = to_decimal(row[col_idx - 1] if col_idx - 1 < len(row) else None)
            if value is None:
                continue
            period_start, period_end = fiscal_period(fy)
            yield FiscalMetricRow(
                state_code=state_code,
                metric_code=metric_code,
                metric_name=metric_name,
                metric_group="debt_issued",
                basis_tag=basis,
                fiscal_year=fy,
                period_start=period_start,
                period_end=period_end,
                value=value,
                unit="INR crore",
                unit_scale="inr_crore",
                provenance=XlsxProvenance(
                    sheet_name=sheet_name,
                    row_number=row_idx,
                    column_index=col_idx,
                    column_label=raw_label,
                    row_label=str(state_cell),
                ),
            )
