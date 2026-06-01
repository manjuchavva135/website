"""RBI Statement 3 — Gross Fiscal Deficit / Surplus.

3 FYs × (Receipts, Expenditure, Surplus(-)/Deficit(+)).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.parsers._fy_subcols import parse_fy_subcols_table
from worker.state_finances_xlsx.records import FiscalMetricRow

_SUBLABELS: dict[str, tuple[str, str]] = {
    "receipts": ("aggregate_receipts_total", "Aggregate Receipts (for fiscal deficit)"),
    "expenditure": ("aggregate_expenditure_total", "Aggregate Expenditure (for fiscal deficit)"),
    "surplus(-)/ deficit(+)": ("gross_fiscal_deficit", "Gross Fiscal Deficit (positive) / Surplus (negative)"),
    "surplus (-)/ deficit (+)": ("gross_fiscal_deficit", "Gross Fiscal Deficit (positive) / Surplus (negative)"),
    "surplus(-)/deficit(+)": ("gross_fiscal_deficit", "Gross Fiscal Deficit (positive) / Surplus (negative)"),
}


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_fy_subcols_table(
        path,
        metric_group="deficit_fiscal",
        sublabel_to_metric=_SUBLABELS,
        unit="INR crore",
        unit_scale="inr_crore",
    )
