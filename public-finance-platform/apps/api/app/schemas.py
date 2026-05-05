from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    status: str
    environment: str


class MetricSeriesResponse(BaseModel):
    slug: str
    title: str
    metric_group: str
    unit: str
    description: str


class MetricObservationResponse(BaseModel):
    id: int
    series_slug: str
    period_start: date
    period_end: date
    period_label: str
    amount: Decimal
    currency: str
    basis: str
    source_document_id: int
    source_row_id: int | None
    provenance_note: str | None


class SourceDocumentResponse(BaseModel):
    id: int
    source_name: str
    publisher: str
    title: str
    source_url: str | None
    document_type: str
    publication_date: date | None
    storage_key: str
    checksum_sha256: str
    parser_version: str
    review_status: str
    review_notes: str | None


class ProvenanceResponse(BaseModel):
    observation_id: int
    document: SourceDocumentResponse
    page_number: int | None
    row_number: int | None
    row_label: str | None
    row_raw_text: str | None


class ReviewQueueItem(BaseModel):
    document_id: int
    source_name: str
    title: str
    parser_version: str
    review_status: str
    checksum_sha256: str
    created_at: datetime


class ReviewUpdateRequest(BaseModel):
    review_status: str
    review_notes: str | None = None


class ChangelogResponse(BaseModel):
    version: str
    title: str
    details: str
    created_at: datetime


class ParserErrorItem(BaseModel):
    id: int
    error_level: str
    error_code: str | None
    message: str
    row_number: int | None
    column_name: str | None
    raw_value: str | None
    created_at: datetime


class AdminParserRunItem(BaseModel):
    id: int
    parser_name: str
    parser_version: str
    status: str
    rows_extracted: int
    warnings_count: int
    started_at: datetime
    completed_at: datetime | None


class AdminExtractedFact(BaseModel):
    target_table: str
    target_id: int
    review_status: str
    confidence_score: Decimal | None
    source_page_id: int | None
    page_number: int | None
    row_number: int | None
    row_label: str | None
    column_name: str | None
    cell_ref: str | None
    quoted_text: str | None
    notes: str | None


class AdminDocumentDetail(BaseModel):
    document_id: int
    source_name: str
    title: str
    review_status: str
    parser_version: str | None
    rows: list[dict[str, object]]
    pages: list[dict[str, object]]
    parser_runs: list[AdminParserRunItem]
    parser_errors: list[ParserErrorItem]
    extracted_facts: list[AdminExtractedFact]


class AdminDocumentListResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int
    page: int
    page_size: int


class AdminStateTransitionRequest(BaseModel):
    to_state: str
    comment: str | None = None


class AdminFactDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str | None = None


class AdminWorkflowStateResponse(BaseModel):
    entity_table: str
    entity_id: int
    state: str


class AdminConflictComparison(BaseModel):
    entity: str
    basis_tag: str
    left_source: str
    left_value: str
    right_source: str
    right_value: str
    difference: str
    metric_code: str | None = None
    period_end: str | None = None
    as_of_date: str | None = None


class AdminRerunParseResponse(BaseModel):
    parser_run_id: int
    task_name: str | None
    status: str


class AdminReleasePublishRequest(BaseModel):
    dataset_name: str
    release_version: str
    release_notes: str
    changelog_title: str
    changelog_details: str


class DatasetReleaseResponse(BaseModel):
    id: int
    dataset_name: str
    release_version: str
    status: str
    release_notes: str | None
    manifest_checksum_sha256: str | None
    manifest_storage_key: str | None
    published_at: datetime | None
    created_at: datetime


class ReviewActionResponse(BaseModel):
    id: int
    entity_table: str
    entity_id: int
    action_type: str
    review_status: str
    actor_email: str | None
    comments: str | None
    acted_at: datetime
    source_document_id: int | None


class ManualUploadResponse(BaseModel):
    document_id: int
    checksum_sha256: str
    storage_key: str
    review_status: str
    duplicate: bool
