"""RBI Statement 1 — Major Fiscal Indicators (% ratios).

Covers two sheets: ST1_1 and ST1_2.

Indicators (ST1_1):
  - Own Revenue / Revenue Expenditure
  - Development Expenditure / Aggregate Disbursement
  - Non-Developmental Expenditure / Aggregate Disbursement
  - Interest Payment / Revenue Expenditure

Indicators (ST1_2):
  - Interest Payment / Revenue Receipts
  - Committed Expenditure / Revenue Expenditure
  - Pension / Revenue Expenditure
  - Gross Transfers / Aggregate Disbursement

All values are percentages.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import (
    fiscal_period,
    fiscal_year_from_label,
    is_column_number_row,
    is_state_header_cell,
    normalize_text,
    open_workbook,
    to_decimal,
)
from worker.state_finances_xlsx.parsers._fy_subcols import _basis_for_fy_label
from worker.state_finances_xlsx.records import FiscalMetricRow, XlsxProvenance
from worker.state_finances_xlsx.state_codes import normalize_state

# Map lowercased indicator text → (metric_code, metric_name)
_SHEET1_INDICATORS: dict[str, tuple[str, str]] = {
    "own revenue/ revenue expenditure": (
        "own_revenue_pct_revenue_expenditure",
        "Own Revenue / Revenue Expenditure (%)",
    ),
    "development expenditure/ aggregate disbursement": (
        "development_expenditure_pct_aggregate",
        "Development Expenditure (% of Aggregate Disbursement)",
    ),
    "non-developmental expenditure/ aggregate disbursement": (
        "non_development_expenditure_pct_aggregate",
        "Non-Developmental Expenditure (% of Aggregate Disbursement)",
    ),
    "interest payment/ revenue expenditure": (
        "interest_pct_revenue_expenditure",
        "Interest Payment (% of Revenue Expenditure)",
    ),
}

_SHEET2_INDICATORS: dict[str, tuple[str, str]] = {
    "interest payment/ revenue receipts": (
        "interest_pct_revenue_receipts",
        "Interest Payment (% of Revenue Receipts)",
    ),
    "committed expenditure/ revenue expenditure": (
        "committed_expenditure_pct_revenue_expenditure",
        "Committed Expenditure (% of Revenue Expenditure)",
    ),
    "pension/ revenue expenditure": (
        "pension_pct_revenue_expenditure",
        "Pension (% of Revenue Expenditure)",
    ),
    "gross transfers/ aggregate disbursement": (
        "gross_transfers_pct_aggregate",
        "Gross Transfers (% of Aggregate Disbursement)",
    ),
}

_METRIC_GROUP = "fiscal_ratios"


def _parse_sheet(
    ws,
    indicator_to_metric: dict[str, tuple[str, str]],
) -> Iterable[FiscalMetricRow]:
    """Parse a single S1 sheet with the indicator-FY-subcols layout."""
    rows = list(ws.iter_rows(values_only=True))
    sheet_name = ws.title

    # Find the indicator header row (contains "State/UT")
    indicator_row_idx: int | None = None
    for i, row in enumerate(rows[:14]):
        if any(is_state_header_cell(cell) for cell in row):
            indicator_row_idx = i
            break
    if indicator_row_idx is None:
        return

    fy_row_idx = indicator_row_idx + 1
    indicator_row = rows[indicator_row_idx]
    fy_row = rows[fy_row_idx] if fy_row_idx < len(rows) else ()

    # Build column map: col_idx → (fy, basis, metric_code, metric_name, raw_label)
    last_indicator: str | None = None
    columns: list[tuple[int, str, str, str, str, str]] = []
    for col_idx in range(3, len(indicator_row) + 1):
        ind_text = normalize_text(indicator_row[col_idx - 1])
        # Strip trailing asterisks and normalize
        if ind_text:
            ind_text = ind_text.rstrip("*").strip()
            last_indicator = ind_text
        if not last_indicator:
            continue
        slug = indicator_to_metric.get(last_indicator.lower())
        if slug is None:
            continue
        fy_label = normalize_text(fy_row[col_idx - 1] if col_idx - 1 < len(fy_row) else None)
        if not fy_label:
            continue
        fy = fiscal_year_from_label(fy_label)
        if not fy:
            continue
        basis = _basis_for_fy_label(fy_label)
        columns.append((col_idx, fy, basis, slug[0], slug[1], f"{last_indicator} | {fy_label}"))

    for row_idx, row in enumerate(rows[fy_row_idx + 1:], start=fy_row_idx + 2):
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
                metric_group=_METRIC_GROUP,
                basis_tag=basis,
                fiscal_year=fy,
                period_start=period_start,
                period_end=period_end,
                value=value,
                unit="percent",
                unit_scale="percent_ratio",
                provenance=XlsxProvenance(
                    sheet_name=sheet_name,
                    row_number=row_idx,
                    column_index=col_idx,
                    column_label=raw_label,
                    row_label=str(state_cell),
                ),
            )


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    wb = open_workbook(str(path))
    sheet_names = wb.sheetnames
    if len(sheet_names) >= 1:
        yield from _parse_sheet(wb[sheet_names[0]], _SHEET1_INDICATORS)
    if len(sheet_names) >= 2:
        yield from _parse_sheet(wb[sheet_names[1]], _SHEET2_INDICATORS)
