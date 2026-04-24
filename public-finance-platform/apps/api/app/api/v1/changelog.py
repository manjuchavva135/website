from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ChangelogEntry
from app.schemas import ChangelogResponse

router = APIRouter(prefix="/changelog", tags=["changelog"])


@router.get("", response_model=list[ChangelogResponse])
def list_changelog(db: Session = Depends(get_db)) -> list[ChangelogResponse]:
    rows = db.scalars(select(ChangelogEntry).order_by(ChangelogEntry.created_at.desc())).all()
    return [
        ChangelogResponse(
            version=row.version,
            title=row.title,
            details=row.details,
            created_at=row.created_at,
        )
        for row in rows
    ]
