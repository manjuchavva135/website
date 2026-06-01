"""RBI Statement 11 — Development Expenditure (₹ Crore)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import parse_year_columns_table
from worker.state_finances_xlsx.records import FiscalMetricRow


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_year_columns_table(
        path,
        metric_code="development_expenditure_total",
        metric_name="Development Expenditure (Total)",
        metric_group="expenditure_capital",
        unit="INR crore",
        unit_scale="inr_crore",
    )
