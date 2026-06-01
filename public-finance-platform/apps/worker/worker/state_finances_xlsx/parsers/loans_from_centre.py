"""RBI Statement 16 — Loans from the Centre (₹ Crore).

3 FYs × (Gross, Net) + Variation. Same shape as S13.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.parsers._fy_subcols import parse_fy_subcols_table
from worker.state_finances_xlsx.records import FiscalMetricRow

_SUBLABELS: dict[str, tuple[str, str]] = {
    "gross": ("loans_from_centre_gross", "Loans from the Centre (Gross)"),
    "net": ("loans_from_centre_net", "Loans from the Centre (Net)"),
    "net*": ("loans_from_centre_net", "Loans from the Centre (Net)"),
}


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_fy_subcols_table(
        path,
        metric_group="receipts_grants",
        sublabel_to_metric=_SUBLABELS,
        unit="INR crore",
        unit_scale="inr_crore",
    )
