"""RBI Statement 14 — Tax Revenue (% of GSDP).

Indicators: Tax Revenue (total), Own Tax Revenue, Share in Central Taxes.
Values are % of GSDP, not ₹ Crore.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.parsers._fy_subcols import parse_indicator_fy_table
from worker.state_finances_xlsx.records import FiscalMetricRow

_INDICATORS: dict[str, tuple[str, str]] = {
    "tax revenue": ("tax_revenue_total_pct_gsdp", "Tax Revenue (% of GSDP)"),
    "own tax revenue": ("own_tax_revenue_pct_gsdp", "Own Tax Revenue (% of GSDP)"),
    "share in central taxes": ("share_central_taxes_pct_gsdp", "Share in Central Taxes (% of GSDP)"),
}


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_indicator_fy_table(
        path,
        metric_group="receipts_tax",
        indicator_to_metric=_INDICATORS,
        unit="percent",
        unit_scale="percent_of_gsdp",
    )
