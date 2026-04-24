from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.cache import read_cache
from app.db.session import SessionLocal
from app.main import app
from app.models import (
    BasisTag,
    DatasetRelease,
    DatasetReleaseStatus,
    DebtEvent,
    DebtEventType,
    DebtInstrument,
    DebtPosition,
    DepartmentSpending,
    FiscalMetric,
    ProvenanceLink,
    SourceDocument,
    SourceDocumentType,
)


def _build_id_allocator(db):
    counters: dict[object, int] = {}

    def _next_id(model) -> int:
        if model not in counters:
            current = db.execute(select(func.max(model.id))).scalar_one_or_none() or 0
            counters[model] = int(current)
        counters[model] += 1
        return counters[model]

    return _next_id


def _seed_api_data() -> None:
    with SessionLocal() as db:
        next_id = _build_id_allocator(db)
        existing = db.scalar(
            select(DebtInstrument.id).where(DebtInstrument.instrument_code == "api_itest_instr")
        )
        if existing:
            return

        source_id = next_id(SourceDocument)
        source = SourceDocument(
            id=source_id,
            source_name="api_test_source",
            publisher="Integration Test",
            source_url="https://example.org/api-test-source",
            canonical_url="https://example.org/api-test-source",
            title="API Integration Source",
            document_type=SourceDocumentType.json,
            mime_type="application/json",
            publication_date=date(2026, 3, 31),
            effective_date=None,
            fiscal_year_label="2025-26",
            checksum_sha256="a" * 64,
            content_length_bytes=128,
            storage_bucket="tests",
            storage_key="tests/api/test-source.json",
            fetch_etag=None,
            parser_version="itest",
            review_status="approved",
            review_notes=None,
            is_active_version=True,
        )
        db.add(source)

        instrument_id = next_id(DebtInstrument)
        instrument = DebtInstrument(
            id=instrument_id,
            source_system="API_TEST",
            instrument_code="api_itest_instr",
            isin=None,
            instrument_name="API Test SDL",
            issuer_name="Government of Andhra Pradesh",
            instrument_type="STATE_LOAN",
            currency="INR",
            coupon_rate=Decimal("7.1000"),
            issue_date=date(2025, 5, 1),
            maturity_date=date(2035, 5, 1),
            is_active=True,
        )
        db.add(instrument)

        debt_position_id = next_id(DebtPosition)
        debt_position = DebtPosition(
            id=debt_position_id,
            debt_instrument_id=instrument_id,
            as_of_date=date(2026, 3, 31),
            basis_tag=BasisTag.audited_actual,
            outstanding_principal=Decimal("1500.00"),
            accrued_interest=Decimal("10.00"),
            face_value=None,
            market_value=None,
        )
        db.add(debt_position)

        events = [
            DebtEvent(
                id=next_id(DebtEvent),
                debt_instrument_id=instrument_id,
                event_type=DebtEventType.issue,
                event_date=date(2025, 5, 1),
                basis_tag=BasisTag.issued,
                amount=Decimal("200.00"),
                units="INR crore",
                counterparty="Andhra Pradesh",
                notes="API test issue",
            ),
            DebtEvent(
                id=next_id(DebtEvent),
                debt_instrument_id=instrument_id,
                event_type=DebtEventType.notification,
                event_date=date(2025, 6, 1),
                basis_tag=BasisTag.scheduled,
                amount=Decimal("250.00"),
                units="INR crore",
                counterparty="Andhra Pradesh",
                notes="API test pipeline",
            ),
            DebtEvent(
                id=next_id(DebtEvent),
                debt_instrument_id=instrument_id,
                event_type=DebtEventType.principal_due,
                event_date=date(2025, 9, 1),
                basis_tag=BasisTag.due,
                amount=Decimal("50.00"),
                units="INR crore",
                counterparty="Andhra Pradesh",
                notes="API test repayment",
            ),
        ]
        for event in events:
            db.add(event)

        fiscal_rows = [
            FiscalMetric(
                id=next_id(FiscalMetric),
                metric_code="api_receipts_total",
                metric_name="API Receipts",
                metric_group="receipts",
                basis_tag=BasisTag.audited_actual,
                fiscal_year="2025-26",
                period_start=date(2025, 4, 1),
                period_end=date(2026, 3, 31),
                value=Decimal("500.00"),
                unit="INR crore",
                department_code=None,
                notes=None,
            ),
            FiscalMetric(
                id=next_id(FiscalMetric),
                metric_code="api_expenditure_total",
                metric_name="API Expenditure",
                metric_group="expenditure",
                basis_tag=BasisTag.audited_actual,
                fiscal_year="2025-26",
                period_start=date(2025, 4, 1),
                period_end=date(2026, 3, 31),
                value=Decimal("600.00"),
                unit="INR crore",
                department_code="edu",
                notes=None,
            ),
            FiscalMetric(
                id=next_id(FiscalMetric),
                metric_code="api_deficit_total",
                metric_name="API Deficit",
                metric_group="deficit",
                basis_tag=BasisTag.audited_actual,
                fiscal_year="2025-26",
                period_start=date(2025, 4, 1),
                period_end=date(2026, 3, 31),
                value=Decimal("100.00"),
                unit="INR crore",
                department_code=None,
                notes=None,
            ),
        ]
        for row in fiscal_rows:
            db.add(row)

        department_spending = DepartmentSpending(
            id=next_id(DepartmentSpending),
            department_code="edu",
            department_name="School Education",
            budget_head_id=None,
            spending_category="revenue",
            basis_tag=BasisTag.audited_actual,
            fiscal_year="2025-26",
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
            amount=Decimal("300.00"),
            unit="INR crore",
        )
        db.add(department_spending)

        release = DatasetRelease(
            id=next_id(DatasetRelease),
            dataset_name="api_test_dataset",
            release_version="v1.0.0",
            status=DatasetReleaseStatus.published,
            release_notes="Integration release",
            manifest_checksum_sha256="b" * 64,
            manifest_storage_key="tests/api/release.json",
            published_at=datetime.now(),
        )
        db.add(release)
        db.flush()

        provenance_targets = [
            ("debt_positions", debt_position_id),
            ("debt_events", events[0].id),
            ("fiscal_metrics", fiscal_rows[0].id),
            ("department_spending", department_spending.id),
        ]
        for table_name, target_id in provenance_targets:
            db.add(
                ProvenanceLink(
                    id=next_id(ProvenanceLink),
                    target_table=table_name,
                    target_id=int(target_id),
                    source_document_id=source_id,
                    source_page_id=None,
                    row_number=1,
                    row_label=f"{table_name}-row",
                    column_name=None,
                    cell_ref=None,
                    quoted_text=f"{table_name} sample quote",
                    parser_run_id=None,
                    confidence_score=Decimal("0.9900"),
                    notes="integration-test",
                )
            )

        db.commit()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        _seed_api_data()
        yield test_client


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/debt/outstanding?financial_year=2025-26&basis=audited_actual&as_of=2026-03-31",
        "/api/v1/debt/issues?financial_year=2025-26",
        "/api/v1/debt/pipeline?financial_year=2025-26",
        "/api/v1/debt/repayments?financial_year=2025-26",
        "/api/v1/fiscal/receipts?financial_year=2025-26",
        "/api/v1/fiscal/expenditure?financial_year=2025-26",
        "/api/v1/fiscal/deficits?financial_year=2025-26",
        "/api/v1/departments/spending?financial_year=2025-26",
        "/api/v1/sources?financial_year=2025-26",
        "/api/v1/releases",
    ],
)
def test_all_requested_endpoints_return_paginated_payloads(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert "pagination" in payload
    assert "sort" in payload


def test_provenance_embedded_for_data_endpoints(client: TestClient) -> None:
    response = client.get(
        "/api/v1/debt/outstanding?financial_year=2025-26&basis=audited_actual&as_of=2026-03-31"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]
    assert "provenance" in payload["data"][0]
    assert isinstance(payload["data"][0]["provenance"], list)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/debt/outstanding?financial_year=2025-26&basis=audited_actual&as_of=2026-03-31&format=csv",
        "/api/v1/debt/issues?financial_year=2025-26&format=csv",
        "/api/v1/debt/pipeline?financial_year=2025-26&format=csv",
        "/api/v1/debt/repayments?financial_year=2025-26&format=csv",
        "/api/v1/fiscal/receipts?financial_year=2025-26&format=csv",
        "/api/v1/fiscal/expenditure?financial_year=2025-26&format=csv",
        "/api/v1/fiscal/deficits?financial_year=2025-26&format=csv",
        "/api/v1/departments/spending?financial_year=2025-26&format=csv",
        "/api/v1/sources?financial_year=2025-26&format=csv",
        "/api/v1/releases?format=csv",
    ],
)
def test_csv_export_supported_for_all_requested_endpoints(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_filter_sort_and_pagination(client: TestClient) -> None:
    response = client.get(
        "/api/v1/debt/issues?financial_year=2025-26&page=1&page_size=1&sort_by=event_date&sort_order=asc"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["page_size"] == 1
    assert payload["sort"]["by"] == "event_date"
    assert payload["sort"]["order"] == "asc"


def test_ambiguous_basis_input_returns_400(client: TestClient) -> None:
    response = client.get("/api/v1/debt/outstanding?basis=audited_actual")
    assert response.status_code == 400


def test_ambiguous_as_of_and_range_returns_400(client: TestClient) -> None:
    response = client.get(
        "/api/v1/debt/outstanding?basis=audited_actual&as_of=2026-03-31&start_date=2025-04-01&end_date=2026-03-31"
    )
    assert response.status_code == 400


def test_cache_hit_header_on_repeat_read(client: TestClient) -> None:
    read_cache.clear()
    path = "/api/v1/fiscal/receipts?financial_year=2025-26"
    first = client.get(path)
    second = client.get(path)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers.get("X-Cache") == "miss"
    assert second.headers.get("X-Cache") == "hit"


def test_openapi_includes_all_public_finance_paths(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    paths = spec["paths"]
    assert "/api/v1/debt/outstanding" in paths
    assert "/api/v1/debt/issues" in paths
    assert "/api/v1/debt/pipeline" in paths
    assert "/api/v1/debt/repayments" in paths
    assert "/api/v1/fiscal/receipts" in paths
    assert "/api/v1/fiscal/expenditure" in paths
    assert "/api/v1/fiscal/deficits" in paths
    assert "/api/v1/departments/spending" in paths
    assert "/api/v1/sources" in paths
    assert "/api/v1/releases" in paths
