"""Tests for the AP budget parser's table-shape heuristics. Real PDF parsing
is exercised end-to-end by the CLI; here we lock in the column-detection
logic that drives row emission."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from worker.ap_budget.budget_parser import (
    _basis_for_category,
    _find_amount_columns,
    _fy_to_period,
    _looks_like_budget_header,
    _to_decimal,
)


def test_looks_like_budget_header_accepts_typical_headers() -> None:
    assert _looks_like_budget_header(["department", "budget estimate", "revised estimate", "actuals"])
    assert _looks_like_budget_header(["scheme", "be 2024-25", "re 2023-24"])
    assert _looks_like_budget_header(["head of account", "actuals 2022-23"])


def test_looks_like_budget_header_rejects_unrelated() -> None:
    assert not _looks_like_budget_header(["item", "qty", "rate"])
    assert not _looks_like_budget_header([])


def test_find_amount_columns_classifies_categories() -> None:
    cols = _find_amount_columns(["department", "be 2024-25", "re 2023-24", "actuals 2022-23"])
    assert cols == [(1, "budget_estimate"), (2, "revised_estimate"), (3, "actuals")]


def test_basis_mapping() -> None:
    assert _basis_for_category("budget_estimate") == "budgeted"
    assert _basis_for_category("revised_estimate") == "revised"
    assert _basis_for_category("actuals") == "actual"


def test_to_decimal_handles_indian_formatting() -> None:
    assert _to_decimal("1,23,456.78") == Decimal("123456.78")
    assert _to_decimal("Rs 9,800") == Decimal("9800")
    assert _to_decimal("-") is None
    assert _to_decimal("") is None


def test_fy_to_period_known_year() -> None:
    start, end = _fy_to_period("2024-25")
    assert start == date(2024, 4, 1)
    assert end == date(2025, 3, 31)
