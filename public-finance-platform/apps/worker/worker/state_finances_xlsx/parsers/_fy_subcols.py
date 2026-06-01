"""Helper for tables with FY in one header row and indicator labels in the next.

Layout (Statement 2, 3, 13, 16, 17):

  R(N)  : 'State/UT', '2023-24 (Accounts)' (merged), '2024-25 (RE)' (merged), ...
  R(N+1): None,        'Indicator A', 'Indicator B', ..., 'Indicator A', 'Indicator B', ...
  R(N+2): col numbers
  R(N+3+): data
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
    open_first_sheet,
    to_decimal,
)
from worker.state_finances_xlsx.records import FiscalMetricRow, XlsxProvenance
from worker.state_finances_xlsx.state_codes import normalize_state


def _basis_for_fy_label(label: str) -> str:
    lower = label.lower()
    if "(be)" in lower or "budget estimate" in lower or "budget" in lower:
        return "budget_estimate"
    if "(re)" in lower or "revised estimate" in lower or "revised" in lower:
        return "revised_estimate"
    if "(p)" in lower or "provisional" in lower:
        return "monthly_actual_provisional"
    return "audited_actual"


def parse_indicator_fy_table(
    path: Path,
    *,
    metric_group: str,
    indicator_to_metric: dict[str, tuple[str, str]],  # lowercased indicator -> (code, name)
    unit: str,
    unit_scale: str,
) -> Iterable[FiscalMetricRow]:
    """Parse tables shaped: indicator merged across N FYs in row N, FY labels in row N+1.

    Layout (Statement 14, 15):

      R(N)  : 'State/UT', 'Tax Revenue' (merged across 3), 'Own Tax Revenue' (merged), ...
      R(N+1): None, '2023-24 (Accounts)', '2024-25 (RE)', '2025-26 (BE)', '2023-24 (Accounts)', ...
      R(N+2): col numbers
      R(N+3+): data
    """
    ws = open_first_sheet(str(path))
    rows = list(ws.iter_rows(values_only=True))
    sheet_name = ws.title

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

    last_indicator: str | None = None
    columns: list[tuple[int, str, str, str, str, str]] = []
    for col_idx in range(3, len(indicator_row) + 1):
        ind_text = normalize_text(indicator_row[col_idx - 1])
        if ind_text:
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

    for row_idx, row in enumerate(rows[fy_row_idx + 1 :], start=fy_row_idx + 2):
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
                metric_group=metric_group,
                basis_tag=basis,
                fiscal_year=fy,
                period_start=period_start,
                period_end=period_end,
                value=value,
                unit=unit,
                unit_scale=unit_scale,
                provenance=XlsxProvenance(
                    sheet_name=sheet_name,
                    row_number=row_idx,
                    column_index=col_idx,
                    column_label=raw_label,
                    row_label=str(state_cell),
                ),
            )


def parse_fy_subcols_table(
    path: Path,
    *,
    metric_group: str,
    sublabel_to_metric: dict[str, tuple[str, str]],  # lowercased sublabel -> (code, name)
    unit: str,
    unit_scale: str,
    skip_columns_with: tuple[str, ...] = ("variation",),
) -> Iterable[FiscalMetricRow]:
    """Parse a two-row-header table where FY is in row N and sublabel in row N+1.

    ``sublabel_to_metric`` maps lowercased sub-column label (e.g., 'revenue receipts')
    to (metric_code, metric_name).
    """
    ws = open_first_sheet(str(path))
    rows = list(ws.iter_rows(values_only=True))
    sheet_name = ws.title

    fy_row_idx: int | None = None
    for i, row in enumerate(rows[:14]):
        if any(is_state_header_cell(cell) for cell in row):
            fy_row_idx = i
            break
    if fy_row_idx is None:
        return
    fy_row = rows[fy_row_idx]

    # Some tables (S13, S16, S17) have a sparse "variation formulas" row between
    # the FY row and the sub-label row. Pick whichever of (fy+1, fy+2) actually
    # contains a known sub-label.
    expected = set(sublabel_to_metric.keys())
    sub_row_idx = fy_row_idx + 1
    for candidate in (fy_row_idx + 1, fy_row_idx + 2):
        if candidate >= len(rows):
            continue
        candidate_row = rows[candidate]
        if any(normalize_text(c).lower() in expected for c in candidate_row):
            sub_row_idx = candidate
            break
    sub_row = rows[sub_row_idx] if sub_row_idx < len(rows) else ()

    # Forward-fill FY labels across merged cells
    last_fy_label: str | None = None
    columns: list[tuple[int, str, str, str, str, str]] = []
    for col_idx in range(3, len(fy_row) + 1):
        fy_text = normalize_text(fy_row[col_idx - 1])
        if fy_text:
            last_fy_label = fy_text
        if not last_fy_label:
            continue
        # Skip 'Variation (Per cent)' columns
        if any(skip in last_fy_label.lower() for skip in skip_columns_with):
            continue
        sub_label = normalize_text(sub_row[col_idx - 1] if col_idx - 1 < len(sub_row) else None)
        if not sub_label:
            continue
        slug = sublabel_to_metric.get(sub_label.lower())
        if slug is None:
            continue
        fy = fiscal_year_from_label(last_fy_label)
        if not fy:
            continue
        basis = _basis_for_fy_label(last_fy_label)
        columns.append((col_idx, fy, basis, slug[0], slug[1], f"{last_fy_label} | {sub_label}"))

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
                metric_group=metric_group,
                basis_tag=basis,
                fiscal_year=fy,
                period_start=period_start,
                period_end=period_end,
                value=value,
                unit=unit,
                unit_scale=unit_scale,
                provenance=XlsxProvenance(
                    sheet_name=sheet_name,
                    row_number=row_idx,
                    column_index=col_idx,
                    column_label=raw_label,
                    row_label=str(state_cell),
                ),
            )
