from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class APFinanceSourceSpec:
    source_family: str
    url: str


@dataclass(frozen=True, slots=True)
class ProvenanceLocator:
    source_url: str
    page_number: int
    row_number: int | None
    row_label: str | None
    quoted_text: str | None


@dataclass(frozen=True, slots=True)
class ReconciliationWarning:
    section: str
    expected_total: Decimal
    computed_total: Decimal
    message: str


@dataclass(frozen=True, slots=True)
class ParsedFiscalMetricRecord:
    metric_code: str
    metric_name: str
    metric_group: str
    basis_tag: str
    fiscal_year: str
    period_start: date
    period_end: date
    value_inr_crore: Decimal
    unit: str
    department_code: str | None
    source_family: str
    parser_confidence: float
    notes: str | None
    provenance: ProvenanceLocator


@dataclass(frozen=True, slots=True)
class ParsedDepartmentSpendingRecord:
    department_code: str
    department_name: str
    spending_category: str
    basis_tag: str
    fiscal_year: str
    period_start: date
    period_end: date
    amount_inr_crore: Decimal
    unit: str
    source_family: str
    parser_confidence: float
    notes: str | None
    provenance: ProvenanceLocator


@dataclass(frozen=True, slots=True)
class ParsedDebtEventRecord:
    instrument_code: str
    instrument_name: str
    issuer_name: str
    event_type: str
    basis_tag: str
    event_date: date
    amount_inr_crore: Decimal
    coupon_or_yield: Decimal | None
    maturity_date: date | None
    tenor: str | None
    source_family: str
    parser_confidence: float
    notes: str | None
    provenance: ProvenanceLocator


@dataclass(frozen=True, slots=True)
class ParsedDebtPositionRecord:
    instrument_code: str
    instrument_name: str
    issuer_name: str
    as_of_date: date
    basis_tag: str
    outstanding_principal_inr_crore: Decimal
    accrued_interest_inr_crore: Decimal | None
    face_value_inr_crore: Decimal | None
    market_value_inr_crore: Decimal | None
    source_family: str
    parser_confidence: float
    notes: str | None
    provenance: ProvenanceLocator
