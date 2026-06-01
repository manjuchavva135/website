"""RBI Statement 2 — Revenue Deficit / Surplus.

3 FYs × (Revenue Receipts, Revenue Expenditure, Revenue Surplus(-)/Deficit(+)).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.parsers._fy_subcols import parse_fy_subcols_table
from worker.state_finances_xlsx.records import FiscalMetricRow

_SUBLABELS: dict[str, tuple[str, str]] = {
    "revenue receipts": ("revenue_receipts_total", "Revenue Receipts (Total)"),
    "revenue expenditure": ("revenue_expenditure_total", "Revenue Expenditure (Total)"),
    "revenue surplus (-)/ deficit (+)": ("revenue_deficit", "Revenue Deficit (positive) / Surplus (negative)"),
    "revenue surplus(-)/ deficit(+)": ("revenue_deficit", "Revenue Deficit (positive) / Surplus (negative)"),
    "revenue surplus (-)/deficit (+)": ("revenue_deficit", "Revenue Deficit (positive) / Surplus (negative)"),
}


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_fy_subcols_table(
        path,
        metric_group="deficit_revenue",
        sublabel_to_metric=_SUBLABELS,
        unit="INR crore",
        unit_scale="inr_crore",
    )
