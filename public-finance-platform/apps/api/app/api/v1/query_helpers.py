from __future__ import annotations

import csv
import io
from datetime import date
from enum import StrEnum
from typing import Any

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import Select
from sqlalchemy.sql.elements import ColumnElement


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


def validate_basis_as_of_ambiguity(
    *,
    basis: str | None,
    as_of: date | None,
    start_date: date | None,
    end_date: date | None,
    financial_year: str | None,
) -> None:
    if (start_date is None) != (end_date is None):
        raise HTTPException(
            status_code=400,
            detail="Date range is ambiguous. Provide both start_date and end_date.",
        )

    if as_of is not None and (start_date is not None or end_date is not None):
        raise HTTPException(
            status_code=400,
            detail="Temporal filter is ambiguous. Use either as_of or start/end date range, not both.",
        )

    if basis is not None and as_of is None and financial_year is None and start_date is None:
        raise HTTPException(
            status_code=400,
            detail="Basis is ambiguous without an anchor. Provide as_of, financial_year, or full date range.",
        )


def apply_sorting(
    query: Select[Any],
    *,
    sort_by: str,
    sort_order: SortOrder,
    allowed_sort_fields: dict[str, ColumnElement[Any]],
) -> Select[Any]:
    column = allowed_sort_fields.get(sort_by)
    if column is None:
        raise HTTPException(status_code=400, detail=f"Unsupported sort_by '{sort_by}'.")
    if sort_order == SortOrder.desc:
        return query.order_by(column.desc())
    return query.order_by(column.asc())


def apply_pagination(query: Select[Any], *, page: int, page_size: int) -> Select[Any]:
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters.")
    return query.offset((page - 1) * page_size).limit(page_size)


def to_csv_response(
    *,
    filename: str,
    rows: list[dict[str, Any]],
    headers: dict[str, str] | None = None,
) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)

    if rows:
        column_headers = list(rows[0].keys())
        writer.writerow(column_headers)
        for row in rows:
            writer.writerow([row.get(header, "") for header in column_headers])

    output.seek(0)
    response_headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Cache-Control": "public, max-age=300, s-maxage=1800, stale-while-revalidate=86400",
    }
    if headers:
        response_headers.update(headers)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers=response_headers,
    )
