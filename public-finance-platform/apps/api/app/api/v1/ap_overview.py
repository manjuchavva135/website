"""State-overview endpoints used by the redesigned homepage and section headers.

Despite the legacy 'ap_overview' naming, these endpoints honor a ``state_code``
query param so the same shape powers AP today and any peer state tomorrow.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["State Overview"])

# Metrics surfaced on the homepage hero. Order is preserved in the response.
_HEADLINE_METRICS: list[tuple[str, str, str]] = [
    # (metric_code, display_label, unit_scale_hint)
    ("total_outstanding_liabilities", "Total Outstanding Debt", "inr_crore"),
    ("total_outstanding_liabilities_pct_gsdp", "Debt-to-GSDP", "percent_of_gsdp"),
    ("gross_fiscal_deficit", "Gross Fiscal Deficit", "inr_crore"),
    ("revenue_deficit", "Revenue Deficit / Surplus", "inr_crore"),
    ("interest_payments_gross", "Interest Payments (Gross)", "inr_crore"),
    ("market_borrowings_gross_raised", "Market Borrowings (Gross)", "inr_crore"),
    ("outstanding_guarantees", "Outstanding Guarantees", "inr_crore"),
    ("devolution_from_centre_net", "Devolution from Centre (Net)", "inr_crore"),
    ("revenue_receipts_total", "Revenue Receipts (Total)", "inr_crore"),
    ("revenue_expenditure_total", "Revenue Expenditure (Total)", "inr_crore"),
    ("development_expenditure_total", "Development Expenditure", "inr_crore"),
    ("non_development_expenditure_total", "Non-Development Expenditure", "inr_crore"),
]


def _cache_headers(response: Response) -> None:
    response.headers["Cache-Control"] = (
        f"public, max-age={settings.public_cache_max_age_seconds}, "
        f"s-maxage={settings.cdn_cache_s_maxage_seconds}, stale-while-revalidate=300"
    )


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@router.get("/ap/headline", summary="State overview headline metrics", tags=["State Overview"])
def ap_headline(
    response: Response,
    state_code: str = Query(default="AP", description="State 2-letter code. Default: AP."),
    db: Session = Depends(get_db),
):
    """Returns one current value per headline metric, plus a small derived ratio block.

    For each metric the API picks the row with the latest ``period_end``; basis_tag and
    fiscal_year are reported alongside so the UI can label values as BE/RE/Actuals.
    """
    rows = db.execute(
        text(
            """
            SELECT DISTINCT ON (metric_code)
                metric_code, metric_name, value, unit, unit_scale, basis_tag,
                fiscal_year, period_start, period_end
            FROM fiscal_metrics
            WHERE state_code = :state_code
              AND department_code IS NULL
              AND metric_code = ANY(:metric_codes)
            ORDER BY metric_code, period_end DESC, basis_tag DESC
            """
        ),
        {
            "state_code": state_code,
            "metric_codes": [m[0] for m in _HEADLINE_METRICS],
        },
    ).fetchall()
    by_code = {r.metric_code: r for r in rows}

    metrics_block: list[dict[str, Any]] = []
    for metric_code, label, _ in _HEADLINE_METRICS:
        row = by_code.get(metric_code)
        if row is None:
            metrics_block.append({"metric_code": metric_code, "label": label, "value": None})
            continue
        metrics_block.append(
            {
                "metric_code": metric_code,
                "label": label,
                "metric_name": row.metric_name,
                "value": _to_float(row.value),
                "unit": row.unit,
                "unit_scale": row.unit_scale,
                "basis_tag": str(row.basis_tag),
                "fiscal_year": row.fiscal_year,
                "period_start": row.period_start,
                "period_end": row.period_end,
            }
        )

    derived: dict[str, Any] = {}
    interest = by_code.get("interest_payments_gross")
    revenue = by_code.get("revenue_receipts_total")
    if interest and revenue and revenue.value:
        derived["interest_pct_revenue_receipts"] = round(
            float(interest.value) / float(revenue.value) * 100.0, 2
        )
    rev_def = by_code.get("revenue_deficit")
    fis_def = by_code.get("gross_fiscal_deficit")
    if rev_def is not None and fis_def is not None:
        derived["fiscal_minus_revenue_deficit"] = round(
            float(fis_def.value) - float(rev_def.value), 2
        )

    _cache_headers(response)
    return {
        "state_code": state_code,
        "metrics": metrics_block,
        "derived": derived,
    }


@router.get("/ap/debt-composition", summary="Debt composition by instrument type (Statement 18)", tags=["State Overview"])
def ap_debt_composition(
    response: Response,
    state_code: str = Query(default="AP", description="State 2-letter code. Default: AP."),
    fiscal_year: str | None = Query(default=None, description="e.g. '2025-26'. Defaults to latest available."),
    db: Session = Depends(get_db),
):
    """Returns the per-instrument outstanding-liabilities breakdown for one (state, fiscal_year)."""
    instrument_codes = [
        "outstanding_sdls_sgs",
        "outstanding_loans_centre",
        "outstanding_provident_fund",
        "outstanding_deposits_advances",
        "outstanding_loans_nabard",
        "outstanding_loans_lic",
        "outstanding_nssf",
        "outstanding_uday",
        "outstanding_compensation_bonds",
        "outstanding_loans_banks_fis",
        "outstanding_loans_other_inst",
        "outstanding_loans_sbi_banks",
        "outstanding_loans_ncdc",
        "outstanding_loans_gic",
        "outstanding_wma_rbi",
        "outstanding_reserve_fund",
        "outstanding_contingency_fund",
        "outstanding_internal_debt",
        "outstanding_total_liabilities_breakdown",
    ]

    if fiscal_year is None:
        latest = db.execute(
            text(
                """
                SELECT fiscal_year FROM fiscal_metrics
                WHERE state_code = :state_code
                  AND department_code IS NULL
                  AND metric_code = 'outstanding_total_liabilities_breakdown'
                ORDER BY period_end DESC LIMIT 1
                """
            ),
            {"state_code": state_code},
        ).scalar_one_or_none()
        fiscal_year = latest

    if fiscal_year is None:
        _cache_headers(response)
        return {"state_code": state_code, "fiscal_year": None, "components": []}

    rows = db.execute(
        text(
            """
            SELECT metric_code, metric_name, value, basis_tag
            FROM fiscal_metrics
            WHERE state_code = :state_code
              AND department_code IS NULL
              AND fiscal_year = :fiscal_year
              AND metric_code = ANY(:metric_codes)
            ORDER BY value DESC NULLS LAST
            """
        ),
        {
            "state_code": state_code,
            "fiscal_year": fiscal_year,
            "metric_codes": instrument_codes,
        },
    ).fetchall()

    components = [
        {
            "metric_code": r.metric_code,
            "label": r.metric_name,
            "value": _to_float(r.value),
            "basis_tag": str(r.basis_tag),
        }
        for r in rows
    ]
    total_row = next((c for c in components if c["metric_code"] == "outstanding_total_liabilities_breakdown"), None)
    components_only = [c for c in components if c["metric_code"] not in {"outstanding_total_liabilities_breakdown", "outstanding_internal_debt"}]

    _cache_headers(response)
    return {
        "state_code": state_code,
        "fiscal_year": fiscal_year,
        "total": total_row["value"] if total_row else None,
        "components": components_only,
    }


@router.get("/ap/maturity-profile", summary="SDL maturity profile by fiscal year (Statement 23 + 24)", tags=["State Overview"])
def ap_maturity_profile(
    response: Response,
    state_code: str = Query(default="AP", description="State 2-letter code. Default: AP."),
    db: Session = Depends(get_db),
):
    """Returns the per-fiscal-year SDL principal due and its share of total outstanding."""
    rows = db.execute(
        text(
            """
            SELECT
              fiscal_year,
              MAX(CASE WHEN metric_code = 'sdl_maturity_principal_due' THEN value END) AS principal_due,
              MAX(CASE WHEN metric_code = 'sdl_maturity_pct_total' THEN value END) AS pct_of_total
            FROM fiscal_metrics
            WHERE state_code = :state_code
              AND department_code IS NULL
              AND metric_code IN ('sdl_maturity_principal_due', 'sdl_maturity_pct_total')
            GROUP BY fiscal_year
            ORDER BY fiscal_year
            """
        ),
        {"state_code": state_code},
    ).fetchall()

    schedule = [
        {
            "fiscal_year": r.fiscal_year,
            "principal_due": _to_float(r.principal_due),
            "pct_of_total": _to_float(r.pct_of_total),
        }
        for r in rows
    ]
    total_principal = sum(s["principal_due"] for s in schedule if s["principal_due"]) or 0.0

    _cache_headers(response)
    return {
        "state_code": state_code,
        "schedule": schedule,
        "total_principal": total_principal,
    }
