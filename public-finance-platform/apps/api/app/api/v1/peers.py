"""Peer-comparison endpoint.

Returns the same metric across multiple states for the same fiscal year (or a
time series of one metric across multiple states). Powers every chart's
'Compare with peers' toggle on the redesigned site.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["Peer Comparison"])


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_states(raw: str) -> list[str]:
    parts = [p.strip().upper() for p in raw.split(",") if p.strip()]
    if not parts:
        raise HTTPException(status_code=400, detail="Provide at least one state code in 'states'.")
    if len(parts) > 12:
        raise HTTPException(status_code=400, detail="Compare at most 12 states at once.")
    return parts


@router.get(
    "/peer-comparison/{metric_code}",
    summary="Same metric across multiple states (single FY) or one state across years",
    tags=["Peer Comparison"],
)
def peer_comparison(
    response: Response,
    metric_code: str,
    states: str = Query(default="AP,TN,KA,TS,MH", description="Comma-separated 2-letter state codes."),
    fiscal_year: str | None = Query(
        default=None,
        description="If provided, returns one row per state for that FY (latest basis). If omitted, returns full time series for each state.",
    ),
    basis: str | None = Query(default=None, description="Optional basis_tag filter."),
    db: Session = Depends(get_db),
):
    state_codes = _parse_states(states)

    if fiscal_year:
        basis_clause = "AND basis_tag = :basis" if basis else ""
        params: dict[str, Any] = {"states": state_codes, "metric_code": metric_code, "fy": fiscal_year}
        if basis:
            params["basis"] = basis
        rows = db.execute(
            text(
                f"""
                SELECT DISTINCT ON (state_code)
                    state_code, metric_code, metric_name, value, unit, unit_scale,
                    basis_tag, fiscal_year, period_start, period_end
                FROM fiscal_metrics
                WHERE state_code = ANY(:states)
                  AND metric_code = :metric_code
                  AND fiscal_year = :fy
                  AND department_code IS NULL
                  {basis_clause}
                ORDER BY state_code, period_end DESC, basis_tag DESC
                """
            ),
            params,
        ).fetchall()
        data = [
            {
                "state_code": r.state_code,
                "metric_code": r.metric_code,
                "metric_name": r.metric_name,
                "value": _to_float(r.value),
                "unit": r.unit,
                "unit_scale": r.unit_scale,
                "basis_tag": str(r.basis_tag),
                "fiscal_year": r.fiscal_year,
                "period_start": r.period_start,
                "period_end": r.period_end,
            }
            for r in rows
        ]
        response.headers["Cache-Control"] = (
            f"public, max-age={settings.public_cache_max_age_seconds}, "
            f"s-maxage={settings.cdn_cache_s_maxage_seconds}"
        )
        return {
            "metric_code": metric_code,
            "fiscal_year": fiscal_year,
            "states_requested": state_codes,
            "data": data,
        }

    # Time-series mode: one row per (state, fiscal_year) — collapse across basis by latest.
    basis_clause = "AND basis_tag = :basis" if basis else ""
    params2: dict[str, Any] = {"states": state_codes, "metric_code": metric_code}
    if basis:
        params2["basis"] = basis
    rows = db.execute(
        text(
            f"""
            SELECT DISTINCT ON (state_code, fiscal_year)
                state_code, metric_code, metric_name, value, unit, unit_scale,
                basis_tag, fiscal_year, period_start, period_end
            FROM fiscal_metrics
            WHERE state_code = ANY(:states)
              AND metric_code = :metric_code
              AND department_code IS NULL
              {basis_clause}
            ORDER BY state_code, fiscal_year, period_end DESC, basis_tag DESC
            """
        ),
        params2,
    ).fetchall()
    series: dict[str, list[dict[str, Any]]] = {sc: [] for sc in state_codes}
    metric_name = None
    unit_scale = None
    for r in rows:
        metric_name = metric_name or r.metric_name
        unit_scale = unit_scale or r.unit_scale
        series.setdefault(r.state_code, []).append(
            {
                "fiscal_year": r.fiscal_year,
                "value": _to_float(r.value),
                "basis_tag": str(r.basis_tag),
            }
        )

    response.headers["Cache-Control"] = (
        f"public, max-age={settings.public_cache_max_age_seconds}, "
        f"s-maxage={settings.cdn_cache_s_maxage_seconds}"
    )
    return {
        "metric_code": metric_code,
        "metric_name": metric_name,
        "unit_scale": unit_scale,
        "states_requested": state_codes,
        "series": series,
    }


@router.get("/peer-comparison/_metrics/catalog", summary="List of metric codes available for peer comparison", tags=["Peer Comparison"])
def peer_metric_catalog(
    response: Response,
    db: Session = Depends(get_db),
):
    """Returns distinct (metric_code, metric_name, unit_scale, metric_group) the UI can offer in a picker."""
    rows = db.execute(
        text(
            """
            SELECT metric_code,
                   MIN(metric_name) AS metric_name,
                   MIN(metric_group) AS metric_group,
                   MIN(unit_scale) AS unit_scale,
                   COUNT(DISTINCT state_code) AS state_count
            FROM fiscal_metrics
            WHERE department_code IS NULL
            GROUP BY metric_code
            ORDER BY metric_code
            """
        )
    ).fetchall()
    response.headers["Cache-Control"] = "public, max-age=600, s-maxage=3600"
    return {
        "metrics": [
            {
                "metric_code": r.metric_code,
                "metric_name": r.metric_name,
                "metric_group": r.metric_group,
                "unit_scale": r.unit_scale,
                "state_count": int(r.state_count),
            }
            for r in rows
        ]
    }
