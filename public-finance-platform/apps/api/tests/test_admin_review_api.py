from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import (
    BasisTag,
    FiscalMetric,
    ParserError,
    ParserErrorLevel,
    ParserRun,
    ReconciliationResult,
    ReconciliationRun,
    ReconciliationStatus,
    ReviewAction,
    RunStatus,
    SourceDocument,
    SourceDocumentType,
    SourcePage,
    SourceRow,
    ProvenanceLink,
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _headers() -> dict[str, str]:
    return {
        "X-Admin-Email": settings.admin_allowed_emails[0],
        "X-Admin-Token": settings.admin_api_token,
    }


def _build_id_allocator(db):
    counters: dict[object, int] = {}

    def _next_id(model) -> int:
        if model not in counters:
            current = db.execute(select(func.max(model.id))).scalar_one_or_none() or 0
            counters[model] = int(current)
        counters[model] += 1
        return counters[model]

    return _next_id


def _seed_admin_data() -> dict[str, int]:
    with SessionLocal() as db:
        existing_doc = db.scalar(select(SourceDocument).where(SourceDocument.source_name == "ap_finance"))
        if existing_doc:
            return {
                "document_id": int(existing_doc.id),
                "fiscal_metric_id": int(db.scalar(select(FiscalMetric.id).where(FiscalMetric.metric_code == "admin_metric_conflict")) or 0),
                "fiscal_metric_alt_id": int(db.scalar(select(FiscalMetric.id).where(FiscalMetric.department_code == "dept_alt")) or 0),
                "reconciliation_result_id": int(db.scalar(select(ReconciliationResult.id).order_by(ReconciliationResult.id.desc()).limit(1)) or 0),
            }

        next_id = _build_id_allocator(db)

        doc1 = SourceDocument(
            id=next_id(SourceDocument),
            source_name="ap_finance",
            publisher="Admin Test",
            source_url="https://example.org/admin/source-1",
            canonical_url="https://example.org/admin/source-1",
            title="Admin Pending Document",
            document_type=SourceDocumentType.json,
            mime_type="application/json",
            publication_date=date(2026, 4, 1),
            effective_date=None,
            fiscal_year_label="2025-26",
            checksum_sha256="c" * 64,
            content_length_bytes=100,
            storage_bucket="tests",
            storage_key="tests/admin/source-1.json",
            fetch_etag=None,
            parser_version="itest-admin",
            review_status="pending",
            review_notes=None,
            is_active_version=True,
        )
        db.add(doc1)

        doc2 = SourceDocument(
            id=next_id(SourceDocument),
            source_name="cag",
            publisher="CAG",
            source_url="https://example.org/admin/source-2",
            canonical_url="https://example.org/admin/source-2",
            title="CAG Document",
            document_type=SourceDocumentType.pdf,
            mime_type="application/pdf",
            publication_date=date(2026, 4, 2),
            effective_date=None,
            fiscal_year_label="2025-26",
            checksum_sha256="d" * 64,
            content_length_bytes=200,
            storage_bucket="tests",
            storage_key="tests/admin/source-2.pdf",
            fetch_etag=None,
            parser_version="itest-admin",
            review_status="approved",
            review_notes=None,
            is_active_version=True,
        )
        db.add(doc2)
        db.flush()

        page = SourcePage(
            id=next_id(SourcePage),
            source_document_id=doc1.id,
            page_number=1,
            page_label="page_1",
            page_checksum_sha256=None,
            extracted_text="row one",
            row_start=1,
            row_end=5,
        )
        db.add(page)

        row = SourceRow(
            id=next_id(SourceRow),
            document_id=doc1.id,
            page_number=1,
            row_number=1,
            row_label="Revenue Receipts",
            raw_text="Revenue Receipts | 1500",
            checksum_sha256="e" * 64,
        )
        db.add(row)

        parser_run = ParserRun(
            id=next_id(ParserRun),
            source_document_id=doc1.id,
            parser_name="admin_parser",
            parser_version="itest-admin",
            status=RunStatus.succeeded,
            config_json=None,
            rows_extracted=1,
            warnings_count=1,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(parser_run)
        db.flush()

        parser_error = ParserError(
            id=next_id(ParserError),
            parser_run_id=parser_run.id,
            source_page_id=page.id,
            row_number=1,
            column_name="amount",
            error_code="warn_value",
            error_level=ParserErrorLevel.warning,
            message="Rounded amount",
            raw_value="1499.995",
            created_at=datetime.now(UTC),
        )
        db.add(parser_error)

        fiscal_1 = FiscalMetric(
            id=next_id(FiscalMetric),
            metric_code="admin_metric_conflict",
            metric_name="Admin Conflict Metric",
            metric_group="receipts",
            basis_tag=BasisTag.audited_actual,
            fiscal_year="2025-26",
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
            value=Decimal("100.00"),
            unit="INR crore",
            department_code=None,
            notes=None,
        )
        db.add(fiscal_1)
        db.flush()

        fiscal_2 = FiscalMetric(
            id=next_id(FiscalMetric),
            metric_code="admin_metric_conflict",
            metric_name="Admin Conflict Metric",
            metric_group="receipts",
            basis_tag=BasisTag.audited_actual,
            fiscal_year="2025-26",
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
            value=Decimal("130.00"),
            unit="INR crore",
            department_code="dept_alt",
            notes=None,
        )
        db.add(fiscal_2)
        db.flush()

        db.add(
            ProvenanceLink(
                id=next_id(ProvenanceLink),
                target_table="fiscal_metrics",
                target_id=fiscal_1.id,
                source_document_id=doc1.id,
                source_page_id=page.id,
                row_number=1,
                row_label="Revenue Receipts",
                column_name=None,
                cell_ref=None,
                quoted_text="Revenue Receipts | 100",
                parser_run_id=parser_run.id,
                confidence_score=Decimal("0.95"),
                notes="admin",
            )
        )
        db.add(
            ProvenanceLink(
                id=next_id(ProvenanceLink),
                target_table="fiscal_metrics",
                target_id=fiscal_2.id,
                source_document_id=doc2.id,
                source_page_id=None,
                row_number=1,
                row_label="Revenue Receipts",
                column_name=None,
                cell_ref=None,
                quoted_text="Revenue Receipts | 130",
                parser_run_id=None,
                confidence_score=Decimal("0.95"),
                notes="admin",
            )
        )

        rec = ReconciliationResult(
            id=next_id(ReconciliationResult),
            reconciliation_run_id=next_id(ReconciliationRun),
            entity_table="fiscal_metrics",
            entity_key="admin_metric_conflict",
            status=ReconciliationStatus.discrepancy,
            left_value="100",
            right_value="130",
            difference_value=Decimal("30.00"),
            notes="seeded discrepancy",
        )
        db.add(
            ReconciliationRun(
                id=rec.reconciliation_run_id,
                run_name="admin_itest_run",
                rule_version="itest",
                status=RunStatus.succeeded,
                scope_json=None,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
        )
        db.add(rec)

        db.commit()
        return {
            "document_id": doc1.id,
            "fiscal_metric_id": fiscal_1.id,
            "fiscal_metric_alt_id": fiscal_2.id,
            "reconciliation_result_id": rec.id,
        }


def test_admin_routes_require_auth(client: TestClient) -> None:
    response = client.get("/api/v1/admin/documents")
    assert response.status_code == 401


def test_list_documents_and_detail(client: TestClient) -> None:
    ids = _seed_admin_data()

    list_resp = client.get("/api/v1/admin/documents", headers=_headers())
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert payload["total"] >= 1

    detail_resp = client.get(f"/api/v1/admin/documents/{ids['document_id']}", headers=_headers())
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["rows"]
    assert detail["parser_runs"]
    assert detail["parser_errors"]
    assert detail["extracted_facts"]


def test_transition_document_records_review_action(client: TestClient) -> None:
    ids = _seed_admin_data()
    resp = client.post(
        f"/api/v1/admin/documents/{ids['document_id']}/transition",
        headers=_headers(),
        json={"to_state": "in_review", "comment": "starting review"},
    )
    assert resp.status_code == 200

    with SessionLocal() as db:
        action = db.scalar(
            select(ReviewAction)
            .where(ReviewAction.entity_table == "source_documents", ReviewAction.entity_id == ids["document_id"])
            .order_by(ReviewAction.id.desc())
            .limit(1)
        )
        assert action is not None
        assert action.review_status == "in_review"


def test_fact_decision_and_conflict_comparison(client: TestClient) -> None:
    ids = _seed_admin_data()

    decide_resp = client.post(
        f"/api/v1/admin/facts/fiscal_metrics/{ids['fiscal_metric_id']}/decision",
        headers=_headers(),
        json={"decision": "approve", "comment": "validated against source"},
    )
    assert decide_resp.status_code == 200

    conflict_resp = client.get("/api/v1/admin/conflicts", headers=_headers())
    assert conflict_resp.status_code == 200
    conflicts = conflict_resp.json()
    assert isinstance(conflicts, list)
    assert any(item["entity"] == "fiscal_metric" for item in conflicts)


def test_invalid_fact_decision_is_rejected(client: TestClient) -> None:
    ids = _seed_admin_data()

    decide_resp = client.post(
        f"/api/v1/admin/facts/fiscal_metrics/{ids['fiscal_metric_id']}/decision",
        headers=_headers(),
        json={"decision": "maybe", "comment": "invalid"},
    )

    assert decide_resp.status_code == 422


def test_annotate_rerun_and_release_flow(client: TestClient) -> None:
    ids = _seed_admin_data()

    note_resp = client.post(
        f"/api/v1/admin/reconciliation/{ids['reconciliation_result_id']}/annotate",
        headers=_headers(),
        json={"to_state": "in_review", "comment": "CAG is authoritative for this period"},
    )
    assert note_resp.status_code == 200

    rerun_resp = client.post(
        f"/api/v1/admin/documents/{ids['document_id']}/rerun-parse",
        headers=_headers(),
    )
    assert rerun_resp.status_code == 200
    assert rerun_resp.json()["status"] == "pending"

    client.post(
        f"/api/v1/admin/documents/{ids['document_id']}/transition",
        headers=_headers(),
        json={"to_state": "approved", "comment": "approved for release"},
    )
    client.post(
        f"/api/v1/admin/facts/fiscal_metrics/{ids['fiscal_metric_id']}/decision",
        headers=_headers(),
        json={"decision": "approve", "comment": "release-ready"},
    )
    client.post(
        f"/api/v1/admin/facts/fiscal_metrics/{ids['fiscal_metric_alt_id']}/decision",
        headers=_headers(),
        json={"decision": "reject", "comment": "conflicting source superseded"},
    )

    release_resp = client.post(
        "/api/v1/admin/releases/publish",
        headers=_headers(),
        json={
            "dataset_name": "andhra_public_finance",
            "release_version": "v2026.04.24-admin-itest",
            "release_notes": "Admin approved release",
            "changelog_title": "Admin release",
            "changelog_details": "Approved facts and published manifest",
        },
    )
    assert release_resp.status_code == 200

    duplicate_resp = client.post(
        "/api/v1/admin/releases/publish",
        headers=_headers(),
        json={
            "dataset_name": "andhra_public_finance",
            "release_version": "v2026.04.24-admin-itest",
            "release_notes": "duplicate",
            "changelog_title": "duplicate",
            "changelog_details": "duplicate",
        },
    )
    assert duplicate_resp.status_code == 409

    history_resp = client.get("/api/v1/admin/releases/history?dataset_name=andhra_public_finance", headers=_headers())
    assert history_resp.status_code == 200
    assert len(history_resp.json()) >= 1
