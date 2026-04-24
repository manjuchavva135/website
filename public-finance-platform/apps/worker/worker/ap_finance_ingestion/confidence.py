from __future__ import annotations

from worker.ap_finance_ingestion.models import (
    ParsedDebtEventRecord,
    ParsedDebtPositionRecord,
    ParsedDepartmentSpendingRecord,
    ParsedFiscalMetricRecord,
)


def score_fiscal_metric(record: ParsedFiscalMetricRecord) -> float:
    present = sum(
        [
            bool(record.metric_code),
            bool(record.metric_name),
            bool(record.basis_tag),
            bool(record.fiscal_year),
            record.value_inr_crore is not None,
            record.provenance.page_number > 0,
        ]
    )
    return round(present / 6, 4)


def score_department_spending(record: ParsedDepartmentSpendingRecord) -> float:
    present = sum(
        [
            bool(record.department_code),
            bool(record.department_name),
            bool(record.spending_category),
            bool(record.basis_tag),
            record.amount_inr_crore is not None,
            record.provenance.page_number > 0,
        ]
    )
    return round(present / 6, 4)


def score_debt_event(record: ParsedDebtEventRecord) -> float:
    present = sum(
        [
            bool(record.instrument_code),
            bool(record.event_type),
            bool(record.basis_tag),
            record.amount_inr_crore is not None,
            record.provenance.page_number > 0,
        ]
    )
    return round(present / 5, 4)


def score_debt_position(record: ParsedDebtPositionRecord) -> float:
    present = sum(
        [
            bool(record.instrument_code),
            bool(record.basis_tag),
            record.outstanding_principal_inr_crore is not None,
            record.provenance.page_number > 0,
        ]
    )
    return round(present / 4, 4)
