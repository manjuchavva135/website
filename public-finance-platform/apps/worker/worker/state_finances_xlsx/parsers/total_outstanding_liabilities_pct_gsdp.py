"""RBI Statement 20 — Total Outstanding Liabilities as % of GSDP."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import parse_year_columns_table
from worker.state_finances_xlsx.records import FiscalMetricRow


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_year_columns_table(
        path,
        metric_code="total_outstanding_liabilities_pct_gsdp",
        metric_name="Total Outstanding Liabilities (% of GSDP)",
        metric_group="debt_outstanding",
        unit="percent",
        unit_scale="percent_of_gsdp",
    )
