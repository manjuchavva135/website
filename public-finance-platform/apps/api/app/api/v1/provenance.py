from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import MetricObservation, SourceRow
from app.schemas import ProvenanceResponse, SourceDocumentResponse

router = APIRouter(prefix="/provenance", tags=["provenance"])


@router.get("/{observation_id}", response_model=ProvenanceResponse)
def get_provenance(observation_id: int, db: Session = Depends(get_db)) -> ProvenanceResponse:
    observation = db.scalar(select(MetricObservation).where(MetricObservation.id == observation_id))
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")

    row = None
    if observation.source_row_id:
        row = db.scalar(select(SourceRow).where(SourceRow.id == observation.source_row_id))

    document = observation.source_document
    return ProvenanceResponse(
        observation_id=observation.id,
        document=SourceDocumentResponse(
            id=document.id,
            source_name=document.source_name,
            publisher=document.publisher,
            title=document.title,
            source_url=document.source_url,
            document_type=document.document_type,
            publication_date=document.publication_date,
            storage_key=document.storage_key,
            checksum_sha256=document.checksum_sha256,
            parser_version=document.parser_version,
            review_status=document.review_status,
            review_notes=document.review_notes,
        ),
        page_number=row.page_number if row else None,
        row_number=row.row_number if row else None,
        row_label=row.row_label if row else None,
        row_raw_text=row.raw_text if row else None,
    )
