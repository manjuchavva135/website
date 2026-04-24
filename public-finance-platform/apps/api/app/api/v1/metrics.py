from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import MetricObservation, MetricSeries
from app.schemas import MetricObservationResponse, MetricSeriesResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=list[MetricSeriesResponse])
def list_series(
    metric_group: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MetricSeriesResponse]:
    query = select(MetricSeries)
    if metric_group:
        query = query.where(MetricSeries.metric_group == metric_group)

    rows = db.scalars(query.order_by(MetricSeries.slug)).all()
    return [
        MetricSeriesResponse(
            slug=row.slug,
            title=row.title,
            metric_group=row.metric_group,
            unit=row.unit,
            description=row.description,
        )
        for row in rows
    ]


@router.get("/{slug}/observations", response_model=list[MetricObservationResponse])
def list_observations(
    slug: str,
    basis: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[MetricObservationResponse]:
    series = db.scalar(select(MetricSeries).where(MetricSeries.slug == slug))
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    query = select(MetricObservation).where(MetricObservation.series_id == series.id)
    if basis:
        query = query.where(MetricObservation.basis == basis)

    rows = db.scalars(query.order_by(MetricObservation.period_start.desc()).limit(limit)).all()

    return [
        MetricObservationResponse(
            id=row.id,
            series_slug=series.slug,
            period_start=row.period_start,
            period_end=row.period_end,
            period_label=row.period_label,
            amount=row.amount,
            currency=row.currency,
            basis=row.basis,
            source_document_id=row.source_document_id,
            source_row_id=row.source_row_id,
            provenance_note=row.provenance_note,
        )
        for row in rows
    ]


@router.get("/{slug}/observations.csv")
def list_observations_csv(
    slug: str,
    basis: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    data = list_observations(slug=slug, basis=basis, limit=limit, db=db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "series_slug",
            "period_start",
            "period_end",
            "period_label",
            "amount",
            "currency",
            "basis",
            "source_document_id",
            "source_row_id",
            "provenance_note",
        ]
    )
    for row in data:
        writer.writerow(
            [
                row.id,
                row.series_slug,
                row.period_start,
                row.period_end,
                row.period_label,
                row.amount,
                row.currency,
                row.basis,
                row.source_document_id,
                row.source_row_id,
                row.provenance_note,
            ]
        )

    output.seek(0)
    filename = f"{slug}-observations.csv"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Cache-Control": "public, max-age=300, s-maxage=1800, stale-while-revalidate=86400",
    }
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)
