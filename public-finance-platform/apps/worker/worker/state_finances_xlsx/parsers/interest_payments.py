"""RBI Statement 13 — Interest Payments (Gross / Net) by state.

3 FYs × (Gross, Net) + Variation (skipped).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.parsers._fy_subcols import parse_fy_subcols_table
from worker.state_finances_xlsx.records import FiscalMetricRow

_SUBLABELS: dict[str, tuple[str, str]] = {
    "gross": ("interest_payments_gross", "Interest Payments (Gross)"),
    "net": ("interest_payments_net", "Interest Payments (Net of recoveries)"),
    "net*": ("interest_payments_net", "Interest Payments (Net of recoveries)"),
}


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_fy_subcols_table(
        path,
        metric_group="debt_outstanding",
        sublabel_to_metric=_SUBLABELS,
        unit="INR crore",
        unit_scale="inr_crore",
    )
