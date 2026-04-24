from __future__ import annotations

from worker.cag_ingestion.models import ParsedCAGDebtPosition, ParsedCAGDepartmentSpending, ParsedCAGFiscalMetric


def score_fiscal_metric(record: ParsedCAGFiscalMetric) -> float:
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


def score_debt_position(record: ParsedCAGDebtPosition) -> float:
    present = sum(
        [
            bool(record.instrument_code),
            bool(record.basis_tag),
            record.outstanding_principal_inr_crore is not None,
            record.provenance.page_number > 0,
        ]
    )
    return round(present / 4, 4)


def score_department_spending(record: ParsedCAGDepartmentSpending) -> float:
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
