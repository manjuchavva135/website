from __future__ import annotations

from decimal import Decimal

from worker.ap_finance_ingestion.models import ReconciliationWarning


def detect_total_mismatch(
    section: str,
    component_amounts: list[Decimal],
    expected_total: Decimal | None,
    tolerance: Decimal = Decimal("0.01"),
) -> ReconciliationWarning | None:
    if expected_total is None:
        return None
    computed = sum(component_amounts, Decimal("0"))
    if abs(computed - expected_total) <= tolerance:
        return None
    return ReconciliationWarning(
        section=section,
        expected_total=expected_total,
        computed_total=computed,
        message=f"{section} does not reconcile: expected {expected_total}, computed {computed}",
    )
