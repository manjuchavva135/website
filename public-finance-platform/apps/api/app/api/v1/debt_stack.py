"""Per-instrument SDL/SGS debt stack: every individual security a state has outstanding.

Powers the Debt Stack page on the redesigned site. Each row exposes ISIN,
nomenclature, coupon, issue/maturity dates, outstanding ₹crore, and a
computed years-to-maturity field.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import DebtInstrument, DebtPosition

router = APIRouter(tags=["Debt"])


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@router.get("/debt/stack", summary="Per-instrument outstanding SDL stack", tags=["Debt"])
def debt_stack(
    response: Response,
    state_code: str = Query(default="AP", description="State 2-letter code. Default: AP."),
    maturity_after: date | None = Query(default=None, description="Only instruments maturing on or after this date."),
    maturity_before: date | None = Query(default=None, description="Only instruments maturing on or before this date."),
    coupon_min: float | None = Query(default=None, ge=0, le=20),
    coupon_max: float | None = Query(default=None, ge=0, le=20),
    search: str | None = Query(default=None, description="Substring of ISIN or nomenclature."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="maturity_date", pattern="^(maturity_date|issue_date|coupon_rate|outstanding_principal|nomenclature)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    sort_map = {
        "maturity_date": DebtInstrument.maturity_date,
        "issue_date": DebtInstrument.issue_date,
        "coupon_rate": DebtInstrument.coupon_rate,
        "outstanding_principal": DebtPosition.outstanding_principal,
        "nomenclature": DebtInstrument.instrument_name,
    }
    column = sort_map[sort_by]
    order_clause = column.asc() if sort_order == "asc" else column.desc()

    # Use the latest known position per instrument (max as_of_date).
    latest_pos_subq = (
        select(
            DebtPosition.debt_instrument_id.label("instrument_id"),
            func.max(DebtPosition.as_of_date).label("as_of_date"),
        )
        .group_by(DebtPosition.debt_instrument_id)
        .subquery()
    )

    base = (
        select(DebtInstrument, DebtPosition)
        .join(latest_pos_subq, latest_pos_subq.c.instrument_id == DebtInstrument.id)
        .join(
            DebtPosition,
            and_(
                DebtPosition.debt_instrument_id == DebtInstrument.id,
                DebtPosition.as_of_date == latest_pos_subq.c.as_of_date,
            ),
        )
        .where(DebtInstrument.issuer_state_code == state_code)
    )

    conditions = []
    if maturity_after:
        conditions.append(DebtInstrument.maturity_date >= maturity_after)
    if maturity_before:
        conditions.append(DebtInstrument.maturity_date <= maturity_before)
    if coupon_min is not None:
        conditions.append(DebtInstrument.coupon_rate >= coupon_min)
    if coupon_max is not None:
        conditions.append(DebtInstrument.coupon_rate <= coupon_max)
    if search:
        like = f"%{search.strip()}%"
        conditions.append(
            (DebtInstrument.isin.ilike(like)) | (DebtInstrument.instrument_name.ilike(like))
        )
    if conditions:
        base = base.where(and_(*conditions))

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = db.execute(base.order_by(order_clause).offset((page - 1) * page_size).limit(page_size)).all()

    today = date.today()
    items: list[dict[str, Any]] = []
    for instrument, position in rows:
        years_to_mat = None
        if instrument.maturity_date:
            days = (instrument.maturity_date - today).days
            years_to_mat = round(days / 365.25, 2)
        items.append(
            {
                "isin": instrument.isin or instrument.instrument_code,
                "nomenclature": instrument.instrument_name,
                "issuer_name": instrument.issuer_name,
                "issuer_state_code": instrument.issuer_state_code,
                "coupon_rate": _to_float(instrument.coupon_rate),
                "issue_date": instrument.issue_date,
                "maturity_date": instrument.maturity_date,
                "years_to_maturity": years_to_mat,
                "outstanding_principal": _to_float(position.outstanding_principal),
                "as_of_date": position.as_of_date,
            }
        )

    aggregates = db.execute(
        select(
            func.count().label("count"),
            func.sum(DebtPosition.outstanding_principal).label("sum"),
            func.avg(DebtInstrument.coupon_rate).label("avg_coupon"),
            func.min(DebtInstrument.maturity_date).label("min_mat"),
            func.max(DebtInstrument.maturity_date).label("max_mat"),
        )
        .select_from(DebtInstrument)
        .join(latest_pos_subq, latest_pos_subq.c.instrument_id == DebtInstrument.id)
        .join(
            DebtPosition,
            and_(
                DebtPosition.debt_instrument_id == DebtInstrument.id,
                DebtPosition.as_of_date == latest_pos_subq.c.as_of_date,
            ),
        )
        .where(DebtInstrument.issuer_state_code == state_code)
    ).one()

    response.headers["Cache-Control"] = (
        f"public, max-age={settings.public_cache_max_age_seconds}, "
        f"s-maxage={settings.cdn_cache_s_maxage_seconds}, stale-while-revalidate=300"
    )

    return {
        "data": items,
        "pagination": {"page": page, "page_size": page_size, "total": int(total)},
        "sort": {"by": sort_by, "order": sort_order},
        "filters_applied": {
            "state_code": state_code,
            "maturity_after": maturity_after,
            "maturity_before": maturity_before,
            "coupon_min": coupon_min,
            "coupon_max": coupon_max,
            "search": search,
        },
        "aggregates_for_state": {
            "total_instruments": int(aggregates.count or 0),
            "total_outstanding_inr_crore": _to_float(aggregates.sum),
            "weighted_average_coupon": _to_float(aggregates.avg_coupon),
            "earliest_maturity": aggregates.min_mat,
            "latest_maturity": aggregates.max_mat,
        },
    }
