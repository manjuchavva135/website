"""RBI Statement 15 — Non-Tax Revenue (% of GSDP).

Indicators: Non-Tax Revenue (total), Own Non-Tax Revenue, Grants.
Values are % of GSDP.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.parsers._fy_subcols import parse_indicator_fy_table
from worker.state_finances_xlsx.records import FiscalMetricRow

_INDICATORS: dict[str, tuple[str, str]] = {
    "non-tax revenue": ("non_tax_revenue_total_pct_gsdp", "Non-Tax Revenue (% of GSDP)"),
    "own non-tax revenue": ("own_non_tax_revenue_pct_gsdp", "Own Non-Tax Revenue (% of GSDP)"),
    "grants": ("grants_pct_gsdp", "Grants from Centre (% of GSDP)"),
}


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_indicator_fy_table(
        path,
        metric_group="receipts_non_tax",
        indicator_to_metric=_INDICATORS,
        unit="percent",
        unit_scale="percent_of_gsdp",
    )
