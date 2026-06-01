"""RBI Statement 29 — Expenditure on Wages and Salaries (₹ Crore)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import parse_year_columns_table
from worker.state_finances_xlsx.records import FiscalMetricRow


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_year_columns_table(
        path,
        metric_code="wages_and_salaries_expenditure",
        metric_name="Expenditure on Wages and Salaries",
        metric_group="expenditure_revenue",
        unit="INR crore",
        unit_scale="inr_crore",
    )
