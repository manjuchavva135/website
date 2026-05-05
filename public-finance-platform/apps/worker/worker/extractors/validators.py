from __future__ import annotations

from worker.extractors.base import ExtractionResult


def validate(result: ExtractionResult) -> list[str]:
    """
    Run cross-cutting sanity checks on an ExtractionResult.
    Returns a list of validation failure messages (empty = all passed).
    """
    failures: list[str] = []
    failures.extend(_check_basis_tags(result))
    failures.extend(_check_period_bounds(result))
    failures.extend(_check_value_signs(result))
    return failures


_VALID_BASIS_TAGS = {
    "audited_actual", "actual", "monthly_actual_provisional", "quarter_actual",
    "budget_estimate", "revised_estimate", "projection", "scheduled",
    "notified", "issued", "due", "paid", "nowcast",
}


def _check_basis_tags(result: ExtractionResult) -> list[str]:
    failures = []
    for records, label in (
        (result.fiscal_metrics, "fiscal_metric"),
        (result.department_spending, "department_spending"),
        (result.debt_events, "debt_event"),
        (result.debt_positions, "debt_position"),
    ):
        for i, rec in enumerate(records):
            tag = getattr(rec, "basis_tag", None)
            if tag and tag not in _VALID_BASIS_TAGS:
                failures.append(f"{label}[{i}]: unknown basis_tag '{tag}'")
    return failures


def _check_period_bounds(result: ExtractionResult) -> list[str]:
    failures = []
    for records, label in (
        (result.fiscal_metrics, "fiscal_metric"),
        (result.department_spending, "department_spending"),
    ):
        for i, rec in enumerate(records):
            start = getattr(rec, "period_start", None)
            end = getattr(rec, "period_end", None)
            if start and end and start > end:
                failures.append(f"{label}[{i}]: period_start {start} > period_end {end}")
    return failures


def _check_value_signs(result: ExtractionResult) -> list[str]:
    """Amounts in INR crore should be non-negative for these record types."""
    failures = []
    for records, field, label in (
        (result.fiscal_metrics, "value_inr_crore", "fiscal_metric"),
        (result.department_spending, "amount_inr_crore", "department_spending"),
        (result.debt_positions, "outstanding_principal_inr_crore", "debt_position"),
    ):
        for i, rec in enumerate(records):
            val = getattr(rec, field, None)
            if val is not None and val < 0:
                failures.append(f"{label}[{i}]: {field} is negative ({val})")
    return failures
