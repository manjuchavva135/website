"""RBI Statement 19 — Total Outstanding Liabilities of State Governments (₹ Crore)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import parse_year_columns_table
from worker.state_finances_xlsx.records import FiscalMetricRow


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_year_columns_table(
        path,
        metric_code="total_outstanding_liabilities",
        metric_name="Total Outstanding Liabilities",
        metric_group="debt_outstanding",
        unit="INR crore",
        unit_scale="inr_crore",
    )
