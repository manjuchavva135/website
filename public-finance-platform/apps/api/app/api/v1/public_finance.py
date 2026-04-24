from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.v1.public_finance_schemas import ApiListResponse
from app.api.v1.query_helpers import to_csv_response, validate_basis_as_of_ambiguity
from app.core.cache import read_cache
from app.core.config import settings
from app.db.session import get_db
from app.models import DebtEventType
from app.services.public_finance_service import PublicFinanceService

router = APIRouter(
    tags=["public-finance"],
)


def _cache_key(path: str, params: dict[str, Any]) -> str:
    serialized_parts: list[str] = []
    for key in sorted(params.keys()):
        if key in {"db", "response", "provider"}:
            continue
        value = params[key]
        if callable(value):
            continue
        if isinstance(value, (str, int, float, bool, type(None), date, datetime)):
            serialized_parts.append(f"{key}={value}")
    serialized = "|".join(serialized_parts)
    return sha256(f"{path}|{serialized}".encode("utf-8")).hexdigest()


def _to_response_payload(*, data: list[dict], page: int, page_size: int, total: int, sort_by: str, sort_order: str) -> dict[str, Any]:
    return {
        "data": data,
        "pagination": {"page": page, "page_size": page_size, "total": total},
        "sort": {"by": sort_by, "order": sort_order},
    }


def _serve_list(
    *,
    path: str,
    params: dict[str, Any],
    format: str,
    filename: str,
    provider,
    response: Response,
):
    json_cache_control = (
        f"public, max-age={settings.public_cache_max_age_seconds}, "
        f"s-maxage={settings.cdn_cache_s_maxage_seconds}, stale-while-revalidate=300"
    )
    csv_cache_control = (
        f"public, max-age={settings.csv_cache_max_age_seconds}, "
        f"s-maxage={settings.csv_cdn_cache_s_maxage_seconds}, stale-while-revalidate=86400"
    )
    key = _cache_key(path, params)
    cached = read_cache.get(key)
    if cached is not None:
        response.headers["X-Cache"] = "hit"
        response.headers["Cache-Control"] = json_cache_control
        if format == "csv":
            return to_csv_response(
                filename=filename,
                rows=cached["data"],
                headers={"X-Cache": "hit", "Cache-Control": csv_cache_control},
            )
        return cached

    payload = provider()
    read_cache.set(key, payload)
    response.headers["X-Cache"] = "miss"
    response.headers["Cache-Control"] = json_cache_control

    if format == "csv":
        return to_csv_response(
            filename=filename,
            rows=payload["data"],
            headers={"X-Cache": "miss", "Cache-Control": csv_cache_control},
        )
    return payload


@router.get(
    "/debt/outstanding",
    response_model=ApiListResponse,
    summary="Outstanding debt stock",
    description="Returns principal debt stock with provenance arrays.",
    tags=["Debt"],
)
def debt_outstanding(
    response: Response,
    financial_year: str | None = Query(default=None, description="Financial year label, e.g. 2025-26"),
    basis: str | None = Query(default=None, description="Basis tag"),
    period_type: str | None = Query(default=None, description="Period type"),
    department: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="as_of_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    validate_basis_as_of_ambiguity(
        basis=basis,
        as_of=as_of,
        start_date=start_date,
        end_date=end_date,
        financial_year=financial_year,
    )
    service = PublicFinanceService(db)

    def provider():
        result = service.list_debt_outstanding(
            financial_year=financial_year,
            basis=basis,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        rows = service.embed_provenance(target_table="debt_positions", items=result.items)
        return _to_response_payload(
            data=rows,
            page=page,
            page_size=page_size,
            total=result.total,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    return _serve_list(
        path="/debt/outstanding",
        params=locals(),
        format=format,
        filename="debt-outstanding.csv",
        provider=provider,
        response=response,
    )


@router.get("/debt/issues", response_model=ApiListResponse, summary="Debt issued", tags=["Debt"])
def debt_issues(
    response: Response,
    financial_year: str | None = Query(default=None),
    basis: str | None = Query(default=None),
    period_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="event_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    validate_basis_as_of_ambiguity(basis=basis, as_of=as_of, start_date=start_date, end_date=end_date, financial_year=financial_year)
    service = PublicFinanceService(db)

    def provider():
        result = service.list_debt_events(
            event_types={DebtEventType.issue},
            financial_year=financial_year,
            basis=basis,
            period_type=period_type,
            department=department,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        rows = service.embed_provenance(target_table="debt_events", items=result.items)
        return _to_response_payload(data=rows, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/debt/issues", params=locals(), format=format, filename="debt-issues.csv", provider=provider, response=response)


@router.get("/debt/pipeline", response_model=ApiListResponse, summary="Scheduled debt pipeline", tags=["Debt"])
def debt_pipeline(
    response: Response,
    financial_year: str | None = Query(default=None),
    basis: str | None = Query(default=None),
    period_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="event_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    validate_basis_as_of_ambiguity(basis=basis, as_of=as_of, start_date=start_date, end_date=end_date, financial_year=financial_year)
    service = PublicFinanceService(db)

    def provider():
        result = service.list_debt_events(
            event_types={DebtEventType.notification},
            financial_year=financial_year,
            basis=basis,
            period_type=period_type,
            department=department,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        rows = service.embed_provenance(target_table="debt_events", items=result.items)
        return _to_response_payload(data=rows, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/debt/pipeline", params=locals(), format=format, filename="debt-pipeline.csv", provider=provider, response=response)


@router.get("/debt/repayments", response_model=ApiListResponse, summary="Debt repayments and service", tags=["Debt"])
def debt_repayments(
    response: Response,
    financial_year: str | None = Query(default=None),
    basis: str | None = Query(default=None),
    period_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="event_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    validate_basis_as_of_ambiguity(basis=basis, as_of=as_of, start_date=start_date, end_date=end_date, financial_year=financial_year)
    service = PublicFinanceService(db)

    def provider():
        result = service.list_debt_events(
            event_types={DebtEventType.principal_due, DebtEventType.principal_paid, DebtEventType.coupon_due, DebtEventType.coupon_paid},
            financial_year=financial_year,
            basis=basis,
            period_type=period_type,
            department=department,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        rows = service.embed_provenance(target_table="debt_events", items=result.items)
        return _to_response_payload(data=rows, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/debt/repayments", params=locals(), format=format, filename="debt-repayments.csv", provider=provider, response=response)


@router.get("/fiscal/receipts", response_model=ApiListResponse, summary="Fiscal receipts", tags=["Fiscal"])
def fiscal_receipts(
    response: Response,
    financial_year: str | None = Query(default=None),
    basis: str | None = Query(default=None),
    period_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="period_start"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    service = PublicFinanceService(db)

    def provider():
        result = service.list_fiscal_metrics(
            metric_group="receipts",
            financial_year=financial_year,
            basis=basis,
            period_type=period_type,
            department=department,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        rows = service.embed_provenance(target_table="fiscal_metrics", items=result.items)
        return _to_response_payload(data=rows, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/fiscal/receipts", params=locals(), format=format, filename="fiscal-receipts.csv", provider=provider, response=response)


@router.get("/fiscal/expenditure", response_model=ApiListResponse, summary="Fiscal expenditure", tags=["Fiscal"])
def fiscal_expenditure(
    response: Response,
    financial_year: str | None = Query(default=None),
    basis: str | None = Query(default=None),
    period_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="period_start"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    service = PublicFinanceService(db)

    def provider():
        result = service.list_fiscal_metrics(
            metric_group="expenditure",
            financial_year=financial_year,
            basis=basis,
            period_type=period_type,
            department=department,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        rows = service.embed_provenance(target_table="fiscal_metrics", items=result.items)
        return _to_response_payload(data=rows, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/fiscal/expenditure", params=locals(), format=format, filename="fiscal-expenditure.csv", provider=provider, response=response)


@router.get("/fiscal/deficits", response_model=ApiListResponse, summary="Fiscal deficits", tags=["Fiscal"])
def fiscal_deficits(
    response: Response,
    financial_year: str | None = Query(default=None),
    basis: str | None = Query(default=None),
    period_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="period_start"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    service = PublicFinanceService(db)

    def provider():
        result = service.list_fiscal_metrics(
            metric_group="deficit",
            financial_year=financial_year,
            basis=basis,
            period_type=period_type,
            department=department,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        rows = service.embed_provenance(target_table="fiscal_metrics", items=result.items)
        return _to_response_payload(data=rows, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/fiscal/deficits", params=locals(), format=format, filename="fiscal-deficits.csv", provider=provider, response=response)


@router.get("/departments/spending", response_model=ApiListResponse, summary="Department spending", tags=["Departments"])
def department_spending(
    response: Response,
    financial_year: str | None = Query(default=None),
    basis: str | None = Query(default=None),
    period_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="period_start"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    service = PublicFinanceService(db)

    def provider():
        result = service.list_department_spending(
            financial_year=financial_year,
            basis=basis,
            department=department,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        rows = service.embed_provenance(target_table="department_spending", items=result.items)
        return _to_response_payload(data=rows, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/departments/spending", params=locals(), format=format, filename="departments-spending.csv", provider=provider, response=response)


@router.get("/sources", response_model=ApiListResponse, summary="Source catalog", tags=["Sources"])
def sources(
    response: Response,
    financial_year: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="publication_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    service = PublicFinanceService(db)

    def provider():
        result = service.list_sources(
            financial_year=financial_year,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return _to_response_payload(data=result.items, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/sources", params=locals(), format=format, filename="sources.csv", provider=provider, response=response)


@router.get("/releases", response_model=ApiListResponse, summary="Dataset releases", tags=["Releases"])
def releases(
    response: Response,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default="published_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    service = PublicFinanceService(db)

    def provider():
        result = service.list_releases(sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size)
        return _to_response_payload(data=result.items, page=page, page_size=page_size, total=result.total, sort_by=sort_by, sort_order=sort_order)

    return _serve_list(path="/releases", params=locals(), format=format, filename="releases.csv", provider=provider, response=response)
