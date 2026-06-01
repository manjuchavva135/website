"""Record types emitted by xlsx parsers and consumed by ``persist``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class XlsxProvenance:
    """Where in the source xlsx this value came from."""

    sheet_name: str
    row_number: int
    column_index: int
    column_label: str | None = None
    row_label: str | None = None
    quoted_text: str | None = None


@dataclass(frozen=True, slots=True)
class FiscalMetricRow:
    """One cell from an RBI statement table, normalized to a fact."""

    state_code: str
    metric_code: str
    metric_name: str
    metric_group: str
    basis_tag: str
    fiscal_year: str
    period_start: date
    period_end: date
    value: Decimal
    unit: str = "INR crore"
    unit_scale: str = "inr_crore"  # inr_crore | percent | percent_of_gsdp | percent_of_revenue | ratio
    department_code: str | None = None
    notes: str | None = None
    provenance: XlsxProvenance | None = None


@dataclass(frozen=True, slots=True)
class DebtInstrumentRow:
    """One per-instrument row from the Outstanding Securities .XLS file."""

    issuer_state_code: str
    issuer_name: str
    instrument_code: str  # ISIN
    instrument_name: str  # nomenclature, e.g. '7.85% ANDHRA SDL 2026'
    instrument_type: str  # 'state_development_loan'
    coupon_rate: Decimal | None
    issue_date: date | None
    maturity_date: date | None
    outstanding_principal: Decimal  # ₹ crore
    as_of_date: date
    provenance: XlsxProvenance | None = None
