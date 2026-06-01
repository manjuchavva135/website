"""RBI Statement 26 — Expenditure on Education as % of Aggregate Expenditure."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import parse_year_columns_table
from worker.state_finances_xlsx.records import FiscalMetricRow


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_year_columns_table(
        path,
        metric_code="education_expenditure_pct_aggregate",
        metric_name="Education Expenditure (% of Aggregate Expenditure)",
        metric_group="expenditure_capital",
        unit="percent",
        unit_scale="percent",
    )
