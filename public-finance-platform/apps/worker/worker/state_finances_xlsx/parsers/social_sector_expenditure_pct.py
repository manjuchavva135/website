"""RBI Statement 32 — Social Sector Expenditure as % of Total Disbursement."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import parse_year_columns_table
from worker.state_finances_xlsx.records import FiscalMetricRow


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_year_columns_table(
        path,
        metric_code="social_sector_expenditure_pct_total",
        metric_name="Social Sector Expenditure (% of Total Disbursement)",
        metric_group="expenditure_capital",
        unit="percent",
        unit_scale="percent",
    )
