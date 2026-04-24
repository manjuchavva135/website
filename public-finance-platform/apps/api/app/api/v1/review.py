from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import AdminPrincipal, require_admin
from app.db.session import get_db
from app.models import DatasetRelease, ReviewAction
from app.schemas import (
    AdminConflictComparison,
    AdminDocumentDetail,
    AdminDocumentListResponse,
    AdminExtractedFact,
    AdminFactDecisionRequest,
    AdminParserRunItem,
    AdminReleasePublishRequest,
    AdminRerunParseResponse,
    AdminStateTransitionRequest,
    AdminWorkflowStateResponse,
    DatasetReleaseResponse,
    ParserErrorItem,
    ReviewActionResponse,
    ReviewQueueItem,
)
from app.services.admin_review_service import AdminReviewService, FactRef

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/review-queue", response_model=list[ReviewQueueItem])
def list_review_queue(
    db: Session = Depends(get_db),
    _: AdminPrincipal = Depends(require_admin),
) -> list[ReviewQueueItem]:
    docs, _total = AdminReviewService(db).list_documents(status="pending", new_only=True, page=1, page_size=100)
    return [
        ReviewQueueItem(
            document_id=item.id,
            source_name=item.source_name,
            title=item.title,
            parser_version=item.parser_version,
            review_status=item.review_status,
            checksum_sha256=item.checksum_sha256,
            created_at=item.created_at,
        )
        for item in docs
    ]


@router.get("/documents", response_model=AdminDocumentListResponse)
def list_documents(
    status: str | None = Query(default=None),
    new_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: AdminPrincipal = Depends(require_admin),
) -> AdminDocumentListResponse:
    docs, total = AdminReviewService(db).list_documents(status=status, new_only=new_only, page=page, page_size=page_size)
    items = [
        ReviewQueueItem(
            document_id=item.id,
            source_name=item.source_name,
            title=item.title,
            parser_version=item.parser_version,
            review_status=item.review_status,
            checksum_sha256=item.checksum_sha256,
            created_at=item.created_at,
        )
        for item in docs
    ]
    return AdminDocumentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/documents/{document_id}", response_model=AdminDocumentDetail)
def get_document_detail(
    document_id: int,
    db: Session = Depends(get_db),
    _: AdminPrincipal = Depends(require_admin),
) -> AdminDocumentDetail:
    service = AdminReviewService(db)
    try:
        doc, rows, pages, parser_runs, errors, facts = service.get_document_rows(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return AdminDocumentDetail(
        document_id=doc.id,
        source_name=doc.source_name,
        title=doc.title,
        review_status=doc.review_status,
        parser_version=doc.parser_version,
        rows=[
            {
                "id": row.id,
                "page_number": row.page_number,
                "row_number": row.row_number,
                "row_label": row.row_label,
                "raw_text": row.raw_text,
                "checksum_sha256": row.checksum_sha256,
            }
            for row in rows
        ],
        pages=[
            {
                "id": page.id,
                "page_number": page.page_number,
                "page_label": page.page_label,
                "row_start": page.row_start,
                "row_end": page.row_end,
            }
            for page in pages
        ],
        parser_runs=[
            AdminParserRunItem(
                id=run.id,
                parser_name=run.parser_name,
                parser_version=run.parser_version,
                status=run.status,
                rows_extracted=run.rows_extracted,
                warnings_count=run.warnings_count,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
            for run in parser_runs
        ],
        parser_errors=[
            ParserErrorItem(
                id=err.id,
                error_level=err.error_level,
                error_code=err.error_code,
                message=err.message,
                row_number=err.row_number,
                column_name=err.column_name,
                raw_value=err.raw_value,
                created_at=err.created_at,
            )
            for err in errors
        ],
        extracted_facts=[
            AdminExtractedFact(
                target_table=fact["target_table"],
                target_id=fact["target_id"],
                review_status=fact["review_status"],
                confidence_score=fact["confidence_score"],
                source_page_id=fact["source_page_id"],
                page_number=fact["page_number"],
                row_number=fact["row_number"],
                row_label=fact["row_label"],
                column_name=fact["column_name"],
                cell_ref=fact["cell_ref"],
                quoted_text=fact["quoted_text"],
                notes=fact["notes"],
            )
            for fact in facts
        ],
    )


@router.post("/documents/{document_id}/transition", response_model=AdminWorkflowStateResponse)
def transition_document(
    document_id: int,
    payload: AdminStateTransitionRequest,
    db: Session = Depends(get_db),
    principal: AdminPrincipal = Depends(require_admin),
) -> AdminWorkflowStateResponse:
    service = AdminReviewService(db)
    try:
        doc = service.transition_document(
            document_id=document_id,
            to_state=payload.to_state,
            actor_email=principal.email,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AdminWorkflowStateResponse(entity_table="source_documents", entity_id=doc.id, state=doc.review_status)


@router.post("/facts/{target_table}/{target_id}/decision", response_model=AdminWorkflowStateResponse)
def decide_fact(
    target_table: str,
    target_id: int,
    payload: AdminFactDecisionRequest,
    db: Session = Depends(get_db),
    principal: AdminPrincipal = Depends(require_admin),
) -> AdminWorkflowStateResponse:
    service = AdminReviewService(db)
    try:
        service.decide_fact(
            fact=FactRef(target_table=target_table, target_id=target_id),
            approve=payload.decision == "approve",
            actor_email=principal.email,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AdminWorkflowStateResponse(
        entity_table=target_table,
        entity_id=target_id,
        state="approved" if payload.decision == "approve" else "rejected",
    )


@router.get("/conflicts", response_model=list[AdminConflictComparison])
def compare_conflicts(
    db: Session = Depends(get_db),
    _: AdminPrincipal = Depends(require_admin),
) -> list[AdminConflictComparison]:
    rows = AdminReviewService(db).compare_conflicts()
    return [AdminConflictComparison.model_validate(row) for row in rows]


@router.post("/reconciliation/{reconciliation_result_id}/annotate", response_model=AdminWorkflowStateResponse)
def annotate_reconciliation(
    reconciliation_result_id: int,
    payload: AdminStateTransitionRequest,
    db: Session = Depends(get_db),
    principal: AdminPrincipal = Depends(require_admin),
) -> AdminWorkflowStateResponse:
    if not payload.comment:
        raise HTTPException(status_code=400, detail="comment is required")
    try:
        AdminReviewService(db).annotate_reconciliation(
            reconciliation_result_id=reconciliation_result_id,
            actor_email=principal.email,
            note=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return AdminWorkflowStateResponse(
        entity_table="reconciliation_results",
        entity_id=reconciliation_result_id,
        state="annotated",
    )


@router.post("/documents/{document_id}/rerun-parse", response_model=AdminRerunParseResponse)
def rerun_parse(
    document_id: int,
    db: Session = Depends(get_db),
    principal: AdminPrincipal = Depends(require_admin),
) -> AdminRerunParseResponse:
    try:
        parser_run, task_name = AdminReviewService(db).rerun_parse(document_id=document_id, actor_email=principal.email)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return AdminRerunParseResponse(parser_run_id=parser_run.id, task_name=task_name, status=parser_run.status)


@router.post("/releases/publish", response_model=DatasetReleaseResponse)
def publish_release(
    payload: AdminReleasePublishRequest,
    db: Session = Depends(get_db),
    principal: AdminPrincipal = Depends(require_admin),
) -> DatasetReleaseResponse:
    try:
        release = AdminReviewService(db).publish_release(
            dataset_name=payload.dataset_name,
            release_version=payload.release_version,
            release_notes=payload.release_notes,
            changelog_title=payload.changelog_title,
            changelog_details=payload.changelog_details,
            actor_email=principal.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return DatasetReleaseResponse(
        id=release.id,
        dataset_name=release.dataset_name,
        release_version=release.release_version,
        status=release.status,
        release_notes=release.release_notes,
        manifest_checksum_sha256=release.manifest_checksum_sha256,
        manifest_storage_key=release.manifest_storage_key,
        published_at=release.published_at,
        created_at=release.created_at,
    )


@router.get("/releases/history", response_model=list[DatasetReleaseResponse])
def release_history(
    dataset_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AdminPrincipal = Depends(require_admin),
) -> list[DatasetReleaseResponse]:
    rows = AdminReviewService(db).list_release_history(dataset_name=dataset_name)
    return [
        DatasetReleaseResponse(
            id=item.id,
            dataset_name=item.dataset_name,
            release_version=item.release_version,
            status=item.status,
            release_notes=item.release_notes,
            manifest_checksum_sha256=item.manifest_checksum_sha256,
            manifest_storage_key=item.manifest_storage_key,
            published_at=item.published_at,
            created_at=item.created_at,
        )
        for item in rows
    ]


@router.get("/audit-trail", response_model=list[ReviewActionResponse])
def audit_trail(
    entity_table: str | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AdminPrincipal = Depends(require_admin),
) -> list[ReviewActionResponse]:
    query = db.query(ReviewAction)
    if entity_table:
        query = query.filter(ReviewAction.entity_table == entity_table)
    if entity_id is not None:
        query = query.filter(ReviewAction.entity_id == entity_id)
    rows = query.order_by(ReviewAction.acted_at.desc(), ReviewAction.id.desc()).limit(500).all()
    return [
        ReviewActionResponse(
            id=item.id,
            entity_table=item.entity_table,
            entity_id=item.entity_id,
            action_type=item.action_type,
            review_status=item.review_status,
            actor_email=item.actor_email,
            comments=item.comments,
            acted_at=item.acted_at,
            source_document_id=item.source_document_id,
        )
        for item in rows
    ]
