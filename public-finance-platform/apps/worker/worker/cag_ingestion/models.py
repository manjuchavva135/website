from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


class CAGDocumentType:
    finance_accounts_vol_i = "finance_accounts_vol_i"
    finance_accounts_vol_ii = "finance_accounts_vol_ii"
    accounts_at_a_glance = "accounts_at_a_glance"
    appropriation_accounts = "appropriation_accounts"
    monthly_key_indicators = "monthly_key_indicators"
    cag_general = "cag_general"


@dataclass(frozen=True, slots=True)
class ProvenanceLocator:
    source_url: str
    page_number: int
    row_number: int | None
    row_label: str | None
    quoted_text: str | None
    table_id: str | None


@dataclass(frozen=True, slots=True)
class ParsedCAGFiscalMetric:
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
    notes: str | None
    parser_confidence: float
    provenance: ProvenanceLocator


@dataclass(frozen=True, slots=True)
class ParsedCAGDebtPosition:
    instrument_code: str
    instrument_name: str
    issuer_name: str
    as_of_date: date
    basis_tag: str
    outstanding_principal_inr_crore: Decimal
    accrued_interest_inr_crore: Decimal | None
    face_value_inr_crore: Decimal | None
    market_value_inr_crore: Decimal | None
    notes: str | None
    parser_confidence: float
    provenance: ProvenanceLocator


@dataclass(frozen=True, slots=True)
class ParsedCAGDepartmentSpending:
    department_code: str
    department_name: str
    spending_category: str
    basis_tag: str
    fiscal_year: str
    period_start: date
    period_end: date
    amount_inr_crore: Decimal
    unit: str
    notes: str | None
    parser_confidence: float
    provenance: ProvenanceLocator


@dataclass(slots=True)
class CAGDocumentParseResult:
    document_family: str
    fiscal_metrics: list[ParsedCAGFiscalMetric] = field(default_factory=list)
    debt_positions: list[ParsedCAGDebtPosition] = field(default_factory=list)
    department_spending: list[ParsedCAGDepartmentSpending] = field(default_factory=list)
    parser_notes: list[str] = field(default_factory=list)
    missing_or_awaited_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
