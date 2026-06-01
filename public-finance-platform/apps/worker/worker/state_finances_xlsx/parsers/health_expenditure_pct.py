"""RBI Statement 27 — Expenditure on Medical/Public Health/Family Welfare as % of Aggregate."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import parse_year_columns_table
from worker.state_finances_xlsx.records import FiscalMetricRow


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_year_columns_table(
        path,
        metric_code="health_expenditure_pct_aggregate",
        metric_name="Medical / Public Health / Family Welfare Expenditure (% of Aggregate)",
        metric_group="expenditure_capital",
        unit="percent",
        unit_scale="percent",
    )
