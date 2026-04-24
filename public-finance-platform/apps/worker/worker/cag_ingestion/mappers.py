from __future__ import annotations

from worker.cag_ingestion.models import ParsedCAGDebtPosition, ParsedCAGDepartmentSpending, ParsedCAGFiscalMetric


def map_to_fiscal_metrics_fields(record: ParsedCAGFiscalMetric) -> dict[str, object]:
    return {
        "target_table": "fiscal_metrics",
        "metric_code": record.metric_code,
        "metric_name": record.metric_name,
        "metric_group": record.metric_group,
        "basis_tag": record.basis_tag,
        "fiscal_year": record.fiscal_year,
        "period_start": record.period_start,
        "period_end": record.period_end,
        "value": record.value_inr_crore,
        "unit": "INR crore",
        "department_code": record.department_code,
        "notes": record.notes,
    }


def map_to_debt_positions_fields(record: ParsedCAGDebtPosition) -> dict[str, object]:
    return {
        "target_table": "debt_positions",
        "instrument_code": record.instrument_code,
        "instrument_name": record.instrument_name,
        "issuer_name": record.issuer_name,
        "as_of_date": record.as_of_date,
        "basis_tag": record.basis_tag,
        "outstanding_principal": record.outstanding_principal_inr_crore,
        "accrued_interest": record.accrued_interest_inr_crore,
        "face_value": record.face_value_inr_crore,
        "market_value": record.market_value_inr_crore,
    }


def map_to_department_spending_fields(record: ParsedCAGDepartmentSpending) -> dict[str, object]:
    return {
        "target_table": "department_spending",
        "department_code": record.department_code,
        "department_name": record.department_name,
        "budget_head_id": None,
        "spending_category": record.spending_category,
        "basis_tag": record.basis_tag,
        "fiscal_year": record.fiscal_year,
        "period_start": record.period_start,
        "period_end": record.period_end,
        "amount": record.amount_inr_crore,
        "unit": "INR crore",
    }
