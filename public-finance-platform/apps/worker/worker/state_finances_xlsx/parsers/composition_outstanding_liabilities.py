"""RBI Statement 18 — Composition of Outstanding Liabilities.

Three sheets, each one as-at-end-March of a year. Columns are the individual
debt instrument categories (SDLs/SGSs, UDAY, NSSF, NABARD, etc.); rows are
states. Each (state, instrument, year) cell becomes one FiscalMetricRow.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import (
    as_at_march_period,
    is_column_number_row,
    is_state_header_cell,
    normalize_text,
    open_workbook,
    to_decimal,
)
from worker.state_finances_xlsx.records import FiscalMetricRow, XlsxProvenance
from worker.state_finances_xlsx.state_codes import normalize_state

_AS_AT_RE = re.compile(r"as\s+at\s+end-march\s+(\d{4})", re.IGNORECASE)

_INSTRUMENT_SLUGS: dict[str, tuple[str, str]] = {
    "sdls/sgss": ("outstanding_sdls_sgs", "Outstanding SDLs/SGSs"),
    "sdls/ sgss": ("outstanding_sdls_sgs", "Outstanding SDLs/SGSs"),
    "uday": ("outstanding_uday", "Outstanding UDAY Bonds"),
    "compensation and other bonds": ("outstanding_compensation_bonds", "Outstanding Compensation & Other Bonds"),
    "nssf": ("outstanding_nssf", "Outstanding NSSF"),
    "wma from rbi": ("outstanding_wma_rbi", "Outstanding Ways & Means Advances from RBI"),
    "loans from lic": ("outstanding_loans_lic", "Outstanding Loans from LIC"),
    "loans from gic": ("outstanding_loans_gic", "Outstanding Loans from GIC"),
    "loans from nabard": ("outstanding_loans_nabard", "Outstanding Loans from NABARD"),
    "loans from sbi and other banks": ("outstanding_loans_sbi_banks", "Outstanding Loans from SBI & Other Banks"),
    "loans fromsbi and other banks": ("outstanding_loans_sbi_banks", "Outstanding Loans from SBI & Other Banks"),
    "loans from ncdc": ("outstanding_loans_ncdc", "Outstanding Loans from NCDC"),
    "loans from other institutions": ("outstanding_loans_other_inst", "Outstanding Loans from Other Institutions"),
    "loans from banks and fis": ("outstanding_loans_banks_fis", "Outstanding Loans from Banks & FIs (subtotal)"),
    "internal debt": ("outstanding_internal_debt", "Outstanding Internal Debt"),
    "loans from centre": ("outstanding_loans_centre", "Outstanding Loans from Centre"),
    "provident fund": ("outstanding_provident_fund", "Outstanding Provident Fund"),
    "reserve fund": ("outstanding_reserve_fund", "Outstanding Reserve Fund"),
    "deposit and advances": ("outstanding_deposits_advances", "Outstanding Deposits & Advances"),
    "depositand advances": ("outstanding_deposits_advances", "Outstanding Deposits & Advances"),
    "contingency fund": ("outstanding_contingency_fund", "Outstanding Contingency Fund"),
    "outstanding liabilities": ("outstanding_total_liabilities_breakdown", "Total Outstanding Liabilities (from composition)"),
}


def _basis_for_year(march_year: int) -> str:
    """Statement 18 publishes T1=actuals, T2=RE, T3=BE relative to publication year."""
    # In the 2025-26 release, T1 covers March 2024 (FY 23-24 actuals),
    # T2 covers March 2025 (FY 24-25 RE), T3 covers March 2026 (FY 25-26 BE).
    if march_year <= 2024:
        return "audited_actual"
    if march_year == 2025:
        return "revised_estimate"
    return "budget_estimate"


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    wb = open_workbook(str(path))
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))

        # Locate the "(As at end-March YYYY)" caption.
        march_year: int | None = None
        for r in rows[:6]:
            for cell in r:
                m = _AS_AT_RE.search(normalize_text(cell))
                if m:
                    march_year = int(m.group(1))
                    break
            if march_year:
                break
        if march_year is None:
            continue

        # Locate the State/UT header row.
        header_row_idx: int | None = None
        for i, row in enumerate(rows[:14]):
            if any(is_state_header_cell(cell) for cell in row):
                header_row_idx = i
                break
        if header_row_idx is None:
            continue

        header_row = rows[header_row_idx]
        col_map: dict[int, tuple[str, str, str]] = {}
        for col_idx in range(3, len(header_row) + 1):
            label = normalize_text(header_row[col_idx - 1])
            if not label:
                continue
            slug = _INSTRUMENT_SLUGS.get(label.lower())
            if slug is None:
                continue
            col_map[col_idx] = (slug[0], slug[1], label)

        period_start, period_end, fiscal_year = as_at_march_period(march_year)
        basis = _basis_for_year(march_year)

        for row_idx, row in enumerate(rows[header_row_idx + 1 :], start=header_row_idx + 2):
            if is_column_number_row(row):
                continue
            state_cell = row[1] if len(row) > 1 else None
            state_code = normalize_state(state_cell)
            if state_code is None:
                continue
            for col_idx, (metric_code, metric_name, raw_label) in col_map.items():
                value = to_decimal(row[col_idx - 1] if col_idx - 1 < len(row) else None)
                if value is None:
                    continue
                yield FiscalMetricRow(
                    state_code=state_code,
                    metric_code=metric_code,
                    metric_name=metric_name,
                    metric_group="debt_outstanding",
                    basis_tag=basis,
                    fiscal_year=fiscal_year,
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
