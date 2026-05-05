from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

from celery import Celery
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    ChangelogEntry,
    DatasetRelease,
    DatasetReleaseStatus,
    DebtEvent,
    DebtPosition,
    DepartmentSpending,
    FiscalMetric,
    ParserError,
    ParserRun,
    ProvenanceLink,
    ReconciliationResult,
    ReviewAction,
    ReviewActionType,
    RunStatus,
    SourceDocument,
    SourceFetchRun,
    SourcePage,
    SourceRow,
)


class ReviewState:
    PENDING = "pending"
    NEW = "new"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


STATE_TRANSITIONS = {
    ReviewState.PENDING: {ReviewState.IN_REVIEW, ReviewState.APPROVED, ReviewState.REJECTED},
    ReviewState.NEW: {ReviewState.IN_REVIEW, ReviewState.APPROVED, ReviewState.REJECTED},
    ReviewState.IN_REVIEW: {ReviewState.APPROVED, ReviewState.REJECTED},
    ReviewState.REJECTED: {ReviewState.IN_REVIEW},
    ReviewState.APPROVED: {ReviewState.PUBLISHED},
    ReviewState.PUBLISHED: set(),
}


FACT_TABLES = {
    "fiscal_metrics": FiscalMetric,
    "debt_positions": DebtPosition,
    "debt_events": DebtEvent,
    "department_spending": DepartmentSpending,
    "reconciliation_results": ReconciliationResult,
}


RUNNER_TASK_BY_SOURCE = {
    "rbi": "worker.tasks.rbi_ingest.fetch_rbi_borrowing_data",
    "ap_finance": "worker.tasks.ap_finance_ingest.fetch_ap_finance_data",
    "cag": "worker.tasks.ingest.fetch_official_sources",
}


@dataclass(frozen=True, slots=True)
class FactRef:
    target_table: str
    target_id: int


class AdminReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_documents(self, *, status: str | None, new_only: bool, page: int, page_size: int) -> tuple[list[SourceDocument], int]:
        query = select(SourceDocument)
        if status:
            query = query.where(SourceDocument.review_status == status)
        if new_only:
            query = query.where(
                or_(
                    SourceDocument.review_status == "pending",
                    SourceDocument.review_status == "needs_manual_review",
                )
            )

        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.db.scalars(
            query.order_by(SourceDocument.created_at.desc(), SourceDocument.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return rows, int(total)

    def get_document_rows(
        self, document_id: int
    ) -> tuple[SourceDocument, list[SourceRow], list[SourcePage], list[ParserRun], list[ParserError], list[dict[str, object]]]:
        doc = self.db.scalar(select(SourceDocument).where(SourceDocument.id == document_id))
        if not doc:
            raise ValueError("Document not found")

        rows = self.db.scalars(
            select(SourceRow)
            .where(SourceRow.document_id == document_id)
            .order_by(SourceRow.page_number.asc().nullsfirst(), SourceRow.row_number.asc().nullsfirst())
        ).all()
        pages = self.db.scalars(
            select(SourcePage)
            .where(SourcePage.source_document_id == document_id)
            .order_by(SourcePage.page_number.asc())
        ).all()
        parser_runs = self.db.scalars(
            select(ParserRun)
            .where(ParserRun.source_document_id == document_id)
            .order_by(ParserRun.started_at.desc(), ParserRun.id.desc())
        ).all()
        errors = self.db.scalars(
            select(ParserError)
            .join(ParserRun, ParserRun.id == ParserError.parser_run_id)
            .where(ParserRun.source_document_id == document_id)
            .order_by(ParserError.created_at.desc())
        ).all()
        fact_rows = self.db.execute(
            select(
                ProvenanceLink.target_table,
                ProvenanceLink.target_id,
                ProvenanceLink.confidence_score,
                ProvenanceLink.source_page_id,
                SourcePage.page_number,
                ProvenanceLink.row_number,
                ProvenanceLink.row_label,
                ProvenanceLink.column_name,
                ProvenanceLink.cell_ref,
                ProvenanceLink.quoted_text,
                ProvenanceLink.notes,
            )
            .outerjoin(SourcePage, SourcePage.id == ProvenanceLink.source_page_id)
            .where(ProvenanceLink.source_document_id == document_id)
            .order_by(
                ProvenanceLink.target_table.asc(),
                ProvenanceLink.target_id.asc(),
                SourcePage.page_number.asc().nullsfirst(),
                ProvenanceLink.row_number.asc().nullsfirst(),
            )
        ).all()
        facts = [
            {
                "target_table": target_table,
                "target_id": target_id,
                "review_status": self.infer_current_state(
                    entity_table=str(target_table),
                    entity_id=int(target_id),
                    fallback=ReviewState.PENDING,
                ),
                "confidence_score": confidence_score,
                "source_page_id": source_page_id,
                "page_number": page_number,
                "row_number": row_number,
                "row_label": row_label,
                "column_name": column_name,
                "cell_ref": cell_ref,
                "quoted_text": quoted_text,
                "notes": notes,
            }
            for (
                target_table,
                target_id,
                confidence_score,
                source_page_id,
                page_number,
                row_number,
                row_label,
                column_name,
                cell_ref,
                quoted_text,
                notes,
            ) in fact_rows
        ]
        return doc, rows, pages, parser_runs, errors, facts

    def infer_current_state(self, *, entity_table: str, entity_id: int, fallback: str = ReviewState.NEW) -> str:
        latest = self.db.scalar(
            select(ReviewAction)
            .where(ReviewAction.entity_table == entity_table, ReviewAction.entity_id == entity_id)
            .order_by(ReviewAction.acted_at.desc(), ReviewAction.id.desc())
            .limit(1)
        )
        if latest:
            return latest.review_status
        return fallback

    def transition_document(self, *, document_id: int, to_state: str, actor_email: str, comment: str | None) -> SourceDocument:
        doc = self.db.scalar(select(SourceDocument).where(SourceDocument.id == document_id))
        if not doc:
            raise ValueError("Document not found")

        from_state = doc.review_status or ReviewState.PENDING
        to_state = self._normalize_review_state(to_state)
        from_state = self._normalize_review_state(from_state)
        if to_state not in STATE_TRANSITIONS.get(from_state, set()):
            raise ValueError(f"Invalid transition: {from_state} -> {to_state}")

        doc.review_status = to_state
        if comment:
            doc.review_notes = comment

        action_type = ReviewActionType.comment
        if to_state == ReviewState.APPROVED:
            action_type = ReviewActionType.approve
        elif to_state == ReviewState.REJECTED:
            action_type = ReviewActionType.reject

        self.db.add(doc)
        self.db.add(
            ReviewAction(
                entity_table="source_documents",
                entity_id=document_id,
                action_type=action_type,
                review_status=to_state,
                actor_email=actor_email,
                comments=comment,
                source_document_id=document_id,
            )
        )
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def decide_fact(self, *, fact: FactRef, approve: bool, actor_email: str, comment: str | None) -> None:
        self._ensure_fact_exists(fact)
        current_state = self.infer_current_state(
            entity_table=fact.target_table,
            entity_id=fact.target_id,
            fallback=ReviewState.PENDING,
        )
        if self._normalize_review_state(current_state) == ReviewState.PUBLISHED:
            raise ValueError("Published facts cannot be changed")
        next_state = ReviewState.APPROVED if approve else ReviewState.REJECTED
        self.db.add(
            ReviewAction(
                entity_table=fact.target_table,
                entity_id=fact.target_id,
                action_type=ReviewActionType.approve if approve else ReviewActionType.reject,
                review_status=next_state,
                actor_email=actor_email,
                comments=comment,
                source_document_id=self._source_document_for_fact(fact),
            )
        )
        self.db.commit()

    def annotate_reconciliation(self, *, reconciliation_result_id: int, actor_email: str, note: str) -> ReconciliationResult:
        rec = self.db.scalar(select(ReconciliationResult).where(ReconciliationResult.id == reconciliation_result_id))
        if not rec:
            raise ValueError("Reconciliation result not found")

        rec.notes = f"{(rec.notes or '').strip()}\n{note}".strip()
        self.db.add(rec)
        self.db.add(
            ReviewAction(
                entity_table="reconciliation_results",
                entity_id=reconciliation_result_id,
                action_type=ReviewActionType.comment,
                review_status="annotated",
                actor_email=actor_email,
                comments=note,
                source_document_id=None,
            )
        )
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def rerun_parse(self, *, document_id: int, actor_email: str) -> tuple[ParserRun, str | None]:
        doc = self.db.scalar(select(SourceDocument).where(SourceDocument.id == document_id))
        if not doc:
            raise ValueError("Document not found")

        parser_run = ParserRun(
            source_document_id=document_id,
            parser_name=f"{doc.source_name}_reparse_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            parser_version=settings.parser_version,
            status=RunStatus.pending,
            config_json=json.dumps({"trigger": "admin-rerun"}),
            rows_extracted=0,
            warnings_count=0,
            started_at=datetime.now(UTC),
            completed_at=None,
        )
        self.db.add(parser_run)
        self.db.add(
            SourceFetchRun(
                source_name=doc.source_name,
                requested_url=doc.source_url,
                resolved_url=doc.canonical_url,
                http_status_code=None,
                status=RunStatus.pending,
                fetched_checksum_sha256=doc.checksum_sha256,
                response_headers_json=None,
                error_message="Admin re-run parse requested",
                source_document_id=document_id,
            )
        )
        self.db.add(
            ReviewAction(
                entity_table="source_documents",
                entity_id=document_id,
                action_type=ReviewActionType.comment,
                review_status="rerun_requested",
                actor_email=actor_email,
                comments="Parser re-run requested by admin",
                source_document_id=document_id,
            )
        )
        self.db.commit()
        self.db.refresh(parser_run)

        task_name = RUNNER_TASK_BY_SOURCE.get(doc.source_name)
        if task_name and settings.dispatch_admin_parser_jobs:
            try:
                Celery(broker=settings.celery_broker_url, backend=settings.celery_result_backend).send_task(
                    task_name,
                    kwargs={"document_id": document_id},
                )
            except Exception:
                task_name = None

        return parser_run, task_name

    def compare_conflicts(self) -> list[dict[str, object]]:
        conflicts: list[dict[str, object]] = []

        fiscal_rows = self.db.execute(
            select(
                FiscalMetric.metric_code,
                FiscalMetric.period_end,
                FiscalMetric.basis_tag,
                SourceDocument.source_name,
                FiscalMetric.value,
            )
            .join(
                ProvenanceLink,
                and_(
                    ProvenanceLink.target_table == "fiscal_metrics",
                    ProvenanceLink.target_id == FiscalMetric.id,
                ),
            )
            .join(SourceDocument, SourceDocument.id == ProvenanceLink.source_document_id)
            .where(SourceDocument.source_name.in_(["cag", "ap_finance", "rbi"]))
        ).all()

        grouped: dict[tuple[str, str, str], dict[str, Decimal]] = {}
        for metric_code, period_end, basis_tag, source_name, value in fiscal_rows:
            key = (str(metric_code), str(period_end), str(basis_tag))
            grouped.setdefault(key, {})[str(source_name)] = Decimal(str(value))

        for key, by_source in grouped.items():
            if len(set(by_source.values())) <= 1 or len(by_source) < 2:
                continue
            min_src, min_val = min(by_source.items(), key=lambda x: x[1])
            max_src, max_val = max(by_source.items(), key=lambda x: x[1])
            conflicts.append(
                {
                    "entity": "fiscal_metric",
                    "metric_code": key[0],
                    "period_end": key[1],
                    "basis_tag": key[2],
                    "left_source": min_src,
                    "left_value": str(min_val),
                    "right_source": max_src,
                    "right_value": str(max_val),
                    "difference": str(max_val - min_val),
                }
            )

        debt_rows = self.db.execute(
            select(
                DebtPosition.as_of_date,
                DebtPosition.basis_tag,
                SourceDocument.source_name,
                DebtPosition.outstanding_principal,
            )
            .join(
                ProvenanceLink,
                and_(
                    ProvenanceLink.target_table == "debt_positions",
                    ProvenanceLink.target_id == DebtPosition.id,
                ),
            )
            .join(SourceDocument, SourceDocument.id == ProvenanceLink.source_document_id)
            .where(SourceDocument.source_name.in_(["cag", "ap_finance", "rbi"]))
        ).all()
        debt_grouped: dict[tuple[str, str], dict[str, Decimal]] = {}
        for as_of_date, basis_tag, source_name, value in debt_rows:
            key = (str(as_of_date), str(basis_tag))
            debt_grouped.setdefault(key, {})[str(source_name)] = Decimal(str(value))

        for key, by_source in debt_grouped.items():
            if len(set(by_source.values())) <= 1 or len(by_source) < 2:
                continue
            min_src, min_val = min(by_source.items(), key=lambda x: x[1])
            max_src, max_val = max(by_source.items(), key=lambda x: x[1])
            conflicts.append(
                {
                    "entity": "debt_position",
                    "as_of_date": key[0],
                    "basis_tag": key[1],
                    "left_source": min_src,
                    "left_value": str(min_val),
                    "right_source": max_src,
                    "right_value": str(max_val),
                    "difference": str(max_val - min_val),
                }
            )

        return conflicts

    def publish_release(
        self,
        *,
        dataset_name: str,
        release_version: str,
        release_notes: str,
        changelog_title: str,
        changelog_details: str,
        actor_email: str,
    ) -> DatasetRelease:
        existing = self.db.scalar(
            select(DatasetRelease).where(
                DatasetRelease.dataset_name == dataset_name,
                DatasetRelease.release_version == release_version,
            )
        )
        if existing:
            raise ValueError("Release version already exists")
        if self._has_unresolved_review_work():
            raise ValueError("Cannot publish while documents or extracted facts are still pending review")

        manifest = self._build_manifest(dataset_name=dataset_name, release_version=release_version)
        manifest_json = json.dumps(manifest, sort_keys=True)
        checksum = sha256(manifest_json.encode("utf-8")).hexdigest()
        manifest_storage_key = f"releases/{dataset_name}/{release_version}/manifest-{checksum[:12]}.json"

        release = DatasetRelease(
            dataset_name=dataset_name,
            release_version=release_version,
            status=DatasetReleaseStatus.published,
            release_notes=release_notes,
            manifest_checksum_sha256=checksum,
            manifest_storage_key=manifest_storage_key,
            published_at=datetime.now(UTC),
        )
        self.db.add(release)
        self.db.add(
            ChangelogEntry(
                version=release_version,
                title=changelog_title,
                details=changelog_details,
            )
        )
        self.db.flush()
        self._mark_approved_documents_published(actor_email=actor_email, release_id=release.id)
        self.db.add(
            ReviewAction(
                entity_table="dataset_releases",
                entity_id=release.id,
                action_type=ReviewActionType.release,
                review_status="published",
                actor_email=actor_email,
                comments=f"Manifest: {manifest_storage_key}",
                source_document_id=None,
            )
        )
        self.db.commit()
        self.db.refresh(release)
        return release

    def list_release_history(self, *, dataset_name: str | None = None) -> list[DatasetRelease]:
        query = select(DatasetRelease)
        if dataset_name:
            query = query.where(DatasetRelease.dataset_name == dataset_name)
        return self.db.scalars(
            query.order_by(DatasetRelease.created_at.desc(), DatasetRelease.id.desc())
        ).all()

    def _build_manifest(self, *, dataset_name: str, release_version: str) -> dict[str, object]:
        approved_docs = self.db.scalars(
            select(SourceDocument).where(SourceDocument.review_status == ReviewState.APPROVED)
        ).all()

        fact_approvals = self.db.execute(
            select(
                ReviewAction.entity_table,
                ReviewAction.review_status,
                func.count().label("count"),
            )
            .where(
                ReviewAction.action_type.in_([ReviewActionType.approve, ReviewActionType.reject]),
                ReviewAction.entity_table.in_([
                    "fiscal_metrics",
                    "debt_positions",
                    "debt_events",
                    "department_spending",
                ]),
            )
            .group_by(ReviewAction.entity_table, ReviewAction.review_status)
        ).all()

        return {
            "dataset_name": dataset_name,
            "release_version": release_version,
            "generated_at": datetime.now(UTC).isoformat(),
            "documents": [
                {
                    "id": doc.id,
                    "source_name": doc.source_name,
                    "checksum_sha256": doc.checksum_sha256,
                    "review_status": doc.review_status,
                }
                for doc in approved_docs
            ],
            "fact_reviews": [
                {
                    "target_table": row.entity_table,
                    "review_status": row.review_status,
                    "count": int(row.count),
                }
                for row in fact_approvals
            ],
        }

    def _ensure_fact_exists(self, fact: FactRef) -> None:
        table_model = FACT_TABLES.get(fact.target_table)

        if table_model is None:
            raise ValueError("Unsupported fact table")

        exists = self.db.scalar(select(table_model).where(table_model.id == fact.target_id))
        if not exists:
            raise ValueError("Fact not found")

    def _source_document_for_fact(self, fact: FactRef) -> int | None:
        return self.db.scalar(
            select(ProvenanceLink.source_document_id)
            .where(
                ProvenanceLink.target_table == fact.target_table,
                ProvenanceLink.target_id == fact.target_id,
            )
            .limit(1)
        )

    def _normalize_review_state(self, state: str | None) -> str:
        if state in (None, "", ReviewState.PENDING):
            return ReviewState.PENDING
        return str(state)

    def _has_unresolved_review_work(self) -> bool:
        unresolved_docs = self.db.scalar(
            select(func.count())
            .select_from(SourceDocument)
            .where(SourceDocument.review_status.in_([ReviewState.PENDING, ReviewState.NEW, ReviewState.IN_REVIEW]))
        ) or 0
        if unresolved_docs:
            return True

        fact_refs = self.db.execute(
            select(ProvenanceLink.target_table, ProvenanceLink.target_id)
            .where(ProvenanceLink.target_table.in_(["fiscal_metrics", "debt_positions", "debt_events", "department_spending"]))
            .group_by(ProvenanceLink.target_table, ProvenanceLink.target_id)
        ).all()
        for target_table, target_id in fact_refs:
            latest_state = self.infer_current_state(
                entity_table=str(target_table),
                entity_id=int(target_id),
                fallback=ReviewState.PENDING,
            )
            if latest_state not in {ReviewState.APPROVED, ReviewState.REJECTED}:
                return True
        return False

    def create_manual_upload(
        self,
        *,
        source_family: str,
        source_name: str,
        title: str,
        document_type: str,
        checksum_sha256: str,
        storage_key: str,
        storage_bucket: str,
        content_length_bytes: int,
        source_url: str | None,
        publication_date: object | None,
        uploaded_by_email: str | None,
        parser_version: str,
        notes: str | None,
    ) -> SourceDocument:
        from app.models import IngestionMode
        doc = SourceDocument(
            source_name=source_name,
            publisher=source_family,
            source_url=source_url,
            canonical_url=source_url,
            title=title,
            document_type=document_type,
            mime_type=None,
            publication_date=publication_date,
            effective_date=None,
            fiscal_year_label=None,
            checksum_sha256=checksum_sha256,
            content_length_bytes=content_length_bytes,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            fetch_etag=None,
            parser_version=parser_version,
            review_status=ReviewState.PENDING,
            review_notes=notes,
            ingestion_mode=IngestionMode.manual_upload,
            uploaded_by_email=uploaded_by_email,
            is_active_version=True,
        )
        self.db.add(doc)
        self.db.flush()
        self.db.add(
            ReviewAction(
                entity_table="source_documents",
                entity_id=doc.id,
                action_type=ReviewActionType.comment,
                review_status=ReviewState.PENDING,
                actor_email=uploaded_by_email,
                comments=f"Manually uploaded via admin UI (source_family={source_family})",
                source_document_id=doc.id,
            )
        )
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def _mark_approved_documents_published(self, *, actor_email: str, release_id: int) -> None:
        approved_docs = self.db.scalars(
            select(SourceDocument).where(SourceDocument.review_status == ReviewState.APPROVED)
        ).all()
        for doc in approved_docs:
            doc.review_status = ReviewState.PUBLISHED
            self.db.add(doc)
            self.db.add(
                ReviewAction(
                    entity_table="source_documents",
                    entity_id=doc.id,
                    action_type=ReviewActionType.release,
                    review_status=ReviewState.PUBLISHED,
                    actor_email=actor_email,
                    comments=f"Published in dataset release {release_id}",
                    source_document_id=doc.id,
                )
            )
