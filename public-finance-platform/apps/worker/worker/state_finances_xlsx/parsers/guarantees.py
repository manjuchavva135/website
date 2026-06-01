"""RBI Statement 28 — Outstanding Guarantees of State Governments (₹ Crore)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from worker.state_finances_xlsx.common import parse_year_columns_table
from worker.state_finances_xlsx.records import FiscalMetricRow


def parse(path: Path) -> Iterable[FiscalMetricRow]:
    yield from parse_year_columns_table(
        path,
        metric_code="outstanding_guarantees",
        metric_name="Outstanding Guarantees",
        metric_group="debt_outstanding",
        unit="INR crore",
        unit_scale="inr_crore",
    )
