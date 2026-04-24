from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceItem(BaseModel):
    source_document_id: int
    source_name: str
    source_url: str
    title: str
    page_number: int | None
    row_number: int | None
    row_label: str | None
    column_name: str | None
    cell_ref: str | None
    quoted_text: str | None
    confidence_score: Decimal | None
    notes: str | None


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int


class SortMeta(BaseModel):
    by: str
    order: Literal["asc", "desc"]


class ApiListResponse(BaseModel):
    data: list[dict]
    pagination: PaginationMeta
    sort: SortMeta


class PublicFinanceFilters(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "financial_year": "2025-26",
                "basis": "audited_actual",
                "period_type": "annual",
                "department": "School Education",
                "start_date": "2025-04-01",
                "end_date": "2026-03-31",
                "as_of": "2026-03-31",
                "page": 1,
                "page_size": 50,
                "sort_by": "as_of_date",
                "sort_order": "desc",
                "format": "json",
            }
        }
    )

    financial_year: str | None = Field(default=None, description="Financial year label, e.g. 2025-26")
    basis: str | None = Field(default=None, description="Basis tag such as audited_actual, actual, budget_estimate")
    period_type: str | None = Field(default=None, description="Period type label, e.g. monthly, quarterly, annual")
    department: str | None = Field(default=None, description="Department code or name filter")
    start_date: date | None = Field(default=None, description="Inclusive period start filter")
    end_date: date | None = Field(default=None, description="Inclusive period end filter")
    as_of: date | None = Field(default=None, description="As-of date for stock-like views")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    sort_by: str = Field(default="created_at")
    sort_order: Literal["asc", "desc"] = Field(default="desc")
    format: Literal["json", "csv"] = Field(default="json")


class DebtOutstandingItem(BaseModel):
    id: int
    as_of_date: date
    financial_year: str | None
    basis: str
    instrument_code: str
    instrument_name: str
    issuer_name: str
    outstanding_principal: Decimal
    accrued_interest: Decimal | None
    provenance: list[ProvenanceItem]


class DebtEventItem(BaseModel):
    id: int
    event_date: date
    financial_year: str | None
    basis: str
    event_type: str
    instrument_code: str
    instrument_name: str
    issuer_name: str
    amount: Decimal
    counterparty: str | None
    notes: str | None
    provenance: list[ProvenanceItem]


class FiscalMetricItem(BaseModel):
    id: int
    metric_code: str
    metric_name: str
    metric_group: str
    financial_year: str
    period_start: date
    period_end: date
    basis: str
    value: Decimal
    unit: str
    department_code: str | None
    provenance: list[ProvenanceItem]


class DepartmentSpendingItem(BaseModel):
    id: int
    department_code: str
    department_name: str
    spending_category: str
    financial_year: str
    period_start: date
    period_end: date
    basis: str
    amount: Decimal
    unit: str
    provenance: list[ProvenanceItem]


class SourceItem(BaseModel):
    id: int
    source_name: str
    publisher: str
    source_url: str
    title: str
    document_type: str
    publication_date: date | None
    fiscal_year_label: str | None
    review_status: str
    parser_version: str | None
    provenance: list[ProvenanceItem] = Field(default_factory=list)


class ReleaseItem(BaseModel):
    id: int
    dataset_name: str
    release_version: str
    status: str
    release_notes: str | None
    published_at: datetime | None
    created_at: datetime
    provenance: list[ProvenanceItem] = Field(default_factory=list)
