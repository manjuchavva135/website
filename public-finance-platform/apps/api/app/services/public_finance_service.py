from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    DatasetRelease,
    DebtEvent,
    DebtEventType,
    DebtInstrument,
    DebtPosition,
    DepartmentSpending,
    FiscalMetric,
    ProvenanceLink,
    SourceDocument,
    SourcePage,
)


@dataclass(slots=True)
class ListResult:
    items: list[dict]
    total: int


class PublicFinanceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_debt_outstanding(
        self,
        *,
        financial_year: str | None,
        basis: str | None,
        start_date: date | None,
        end_date: date | None,
        as_of: date | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
        state_code: str | None = None,
    ) -> ListResult:
        query = select(DebtPosition, DebtInstrument).join(DebtInstrument, DebtInstrument.id == DebtPosition.debt_instrument_id)

        conditions = []
        if state_code:
            conditions.append(DebtInstrument.issuer_state_code == state_code)
        if basis:
            conditions.append(DebtPosition.basis_tag == basis)
        if as_of:
            conditions.append(DebtPosition.as_of_date <= as_of)
        if start_date and end_date:
            conditions.append(and_(DebtPosition.as_of_date >= start_date, DebtPosition.as_of_date <= end_date))

        if conditions:
            query = query.where(and_(*conditions))

        sort_map = {
            "as_of_date": DebtPosition.as_of_date,
            "outstanding_principal": DebtPosition.outstanding_principal,
            "instrument_code": DebtInstrument.instrument_code,
            "created_at": DebtPosition.id,
        }
        query = self._apply_sort(query, sort_map, sort_by, sort_order)

        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        page_rows = self.db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()

        items = []
        for position, instrument in page_rows:
            items.append(
                {
                    "id": int(position.id),
                    "as_of_date": position.as_of_date,
                    "financial_year": financial_year,
                    "basis": position.basis_tag.value if hasattr(position.basis_tag, "value") else str(position.basis_tag),
                    "instrument_code": instrument.instrument_code,
                    "instrument_name": instrument.instrument_name,
                    "issuer_name": instrument.issuer_name,
                    "outstanding_principal": position.outstanding_principal,
                    "accrued_interest": position.accrued_interest,
                }
            )
        return ListResult(items=items, total=int(total))

    def list_debt_events(
        self,
        *,
        event_types: set[DebtEventType],
        financial_year: str | None,
        basis: str | None,
        period_type: str | None,
        start_date: date | None,
        end_date: date | None,
        department: str | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
        state_code: str | None = None,
    ) -> ListResult:
        query = select(DebtEvent, DebtInstrument).join(DebtInstrument, DebtInstrument.id == DebtEvent.debt_instrument_id)

        conditions = [DebtEvent.event_type.in_(event_types)]
        if state_code:
            conditions.append(DebtInstrument.issuer_state_code == state_code)
        if basis:
            conditions.append(DebtEvent.basis_tag == basis)
        if start_date and end_date:
            conditions.append(and_(DebtEvent.event_date >= start_date, DebtEvent.event_date <= end_date))
        if department:
            conditions.append(DebtEvent.counterparty.ilike(f"%{department}%"))

        query = query.where(and_(*conditions))

        sort_map = {
            "event_date": DebtEvent.event_date,
            "amount": DebtEvent.amount,
            "instrument_code": DebtInstrument.instrument_code,
            "created_at": DebtEvent.id,
        }
        query = self._apply_sort(query, sort_map, sort_by, sort_order)

        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        page_rows = self.db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()

        items = []
        for event, instrument in page_rows:
            items.append(
                {
                    "id": int(event.id),
                    "event_date": event.event_date,
                    "financial_year": financial_year,
                    "basis": event.basis_tag.value if hasattr(event.basis_tag, "value") else str(event.basis_tag),
                    "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                    "instrument_code": instrument.instrument_code,
                    "instrument_name": instrument.instrument_name,
                    "issuer_name": instrument.issuer_name,
                    "amount": event.amount,
                    "counterparty": event.counterparty,
                    "notes": event.notes,
                }
            )
        return ListResult(items=items, total=int(total))

    def list_fiscal_metrics(
        self,
        *,
        metric_group: str,
        financial_year: str | None,
        basis: str | None,
        period_type: str | None,
        department: str | None,
        start_date: date | None,
        end_date: date | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
        state_code: str | None = None,
    ) -> ListResult:
        # RBI xlsx metric groups are stored with sub-domain suffixes
        # (deficit_fiscal / deficit_revenue, receipts_tax / receipts_non_tax /
        # receipts_grants, expenditure_revenue / expenditure_capital, etc.).
        # Match the API-facing group as a prefix so an exact equality on the
        # legacy short name (e.g. "deficit") still returns all relevant rows.
        query = select(FiscalMetric).where(
            or_(
                FiscalMetric.metric_group == metric_group,
                FiscalMetric.metric_group.like(f"{metric_group}_%"),
            )
        )

        conditions = [FiscalMetric.department_code.is_(None)]
        if state_code:
            conditions.append(FiscalMetric.state_code == state_code)
        if financial_year:
            conditions.append(FiscalMetric.fiscal_year == financial_year)
        if basis:
            conditions.append(FiscalMetric.basis_tag == basis)
        if department:
            conditions.append(FiscalMetric.department_code.ilike(f"%{department}%"))
        if start_date and end_date:
            conditions.append(and_(FiscalMetric.period_start >= start_date, FiscalMetric.period_end <= end_date))

        if conditions:
            query = query.where(and_(*conditions))

        sort_map = {
            "period_start": FiscalMetric.period_start,
            "period_end": FiscalMetric.period_end,
            "value": FiscalMetric.value,
            "metric_code": FiscalMetric.metric_code,
            "created_at": FiscalMetric.id,
        }
        query = self._apply_sort(query, sort_map, sort_by, sort_order)

        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        page_rows = self.db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()

        items = []
        for metric in page_rows:
            items.append(
                {
                    "id": int(metric.id),
                    "metric_code": metric.metric_code,
                    "metric_name": metric.metric_name,
                    "metric_group": metric.metric_group,
                    "financial_year": metric.fiscal_year,
                    "period_start": metric.period_start,
                    "period_end": metric.period_end,
                    "basis": metric.basis_tag.value if hasattr(metric.basis_tag, "value") else str(metric.basis_tag),
                    "value": metric.value,
                    "unit": metric.unit,
                    "department_code": metric.department_code,
                }
            )
        return ListResult(items=items, total=int(total))

    def list_department_spending(
        self,
        *,
        financial_year: str | None,
        basis: str | None,
        department: str | None,
        start_date: date | None,
        end_date: date | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
        state_code: str | None = None,  # noqa: ARG002 — DepartmentSpending is AP-only today
    ) -> ListResult:
        query = select(DepartmentSpending)

        conditions = []
        if financial_year:
            conditions.append(DepartmentSpending.fiscal_year == financial_year)
        if basis:
            conditions.append(DepartmentSpending.basis_tag == basis)
        if department:
            conditions.append(
                or_(
                    DepartmentSpending.department_code.ilike(f"%{department}%"),
                    DepartmentSpending.department_name.ilike(f"%{department}%"),
                )
            )
        if start_date and end_date:
            conditions.append(and_(DepartmentSpending.period_start >= start_date, DepartmentSpending.period_end <= end_date))

        if conditions:
            query = query.where(and_(*conditions))

        sort_map = {
            "period_start": DepartmentSpending.period_start,
            "amount": DepartmentSpending.amount,
            "department_code": DepartmentSpending.department_code,
            "created_at": DepartmentSpending.id,
        }
        query = self._apply_sort(query, sort_map, sort_by, sort_order)

        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        page_rows = self.db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()

        items = []
        for row in page_rows:
            items.append(
                {
                    "id": int(row.id),
                    "department_code": row.department_code,
                    "department_name": row.department_name,
                    "spending_category": row.spending_category,
                    "financial_year": row.fiscal_year,
                    "period_start": row.period_start,
                    "period_end": row.period_end,
                    "basis": row.basis_tag.value if hasattr(row.basis_tag, "value") else str(row.basis_tag),
                    "amount": row.amount,
                    "unit": row.unit,
                }
            )
        return ListResult(items=items, total=int(total))

    def list_sources(
        self,
        *,
        financial_year: str | None,
        start_date: date | None,
        end_date: date | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> ListResult:
        query = select(SourceDocument)

        conditions = []
        if financial_year:
            conditions.append(SourceDocument.fiscal_year_label == financial_year)
        if start_date and end_date:
            conditions.append(and_(SourceDocument.publication_date >= start_date, SourceDocument.publication_date <= end_date))
        if conditions:
            query = query.where(and_(*conditions))

        sort_map = {
            "publication_date": SourceDocument.publication_date,
            "source_name": SourceDocument.source_name,
            "created_at": SourceDocument.created_at,
        }
        query = self._apply_sort(query, sort_map, sort_by, sort_order)

        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        rows = self.db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        items = [
            {
                "id": int(row.id),
                "source_name": row.source_name,
                "publisher": row.publisher,
                "source_url": row.source_url,
                "title": row.title,
                "document_type": row.document_type.value if hasattr(row.document_type, "value") else str(row.document_type),
                "publication_date": row.publication_date,
                "fiscal_year_label": row.fiscal_year_label,
                "review_status": row.review_status,
                "parser_version": row.parser_version,
            }
            for row in rows
        ]
        return ListResult(items=items, total=int(total))

    def list_releases(
        self,
        *,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> ListResult:
        query = select(DatasetRelease)
        sort_map = {
            "published_at": DatasetRelease.published_at,
            "created_at": DatasetRelease.created_at,
            "dataset_name": DatasetRelease.dataset_name,
        }
        query = self._apply_sort(query, sort_map, sort_by, sort_order)

        total = self.db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        rows = self.db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        items = [
            {
                "id": int(row.id),
                "dataset_name": row.dataset_name,
                "release_version": row.release_version,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "release_notes": row.release_notes,
                "published_at": row.published_at,
                "created_at": row.created_at,
            }
            for row in rows
        ]
        return ListResult(items=items, total=int(total))

    def embed_provenance(self, *, target_table: str, items: list[dict]) -> list[dict]:
        target_ids = [int(item["id"]) for item in items]
        if not target_ids:
            return items

        links = self.db.execute(
            select(ProvenanceLink, SourceDocument, SourcePage)
            .join(SourceDocument, SourceDocument.id == ProvenanceLink.source_document_id)
            .outerjoin(SourcePage, SourcePage.id == ProvenanceLink.source_page_id)
            .where(ProvenanceLink.target_table == target_table, ProvenanceLink.target_id.in_(target_ids))
            .order_by(ProvenanceLink.id.asc())
        ).all()

        grouped: dict[int, list[dict]] = defaultdict(list)
        for link, source_document, source_page in links:
            grouped[int(link.target_id)].append(
                {
                    "source_document_id": int(source_document.id),
                    "source_name": source_document.source_name,
                    "source_url": source_document.source_url,
                    "title": source_document.title,
                    "page_number": source_page.page_number if source_page else None,
                    "row_number": link.row_number,
                    "row_label": link.row_label,
                    "column_name": link.column_name,
                    "cell_ref": link.cell_ref,
                    "quoted_text": link.quoted_text,
                    "confidence_score": link.confidence_score,
                    "notes": link.notes,
                }
            )

        for item in items:
            item["provenance"] = grouped.get(int(item["id"]), [])
        return items

    @staticmethod
    def _apply_sort(query, sort_map: dict[str, object], sort_by: str, sort_order: str):
        column = sort_map.get(sort_by)
        if column is None:
            column = sort_map.get("created_at")
        if column is None:
            column = next(iter(sort_map.values()))
        if sort_order == "asc":
            return query.order_by(column.asc())
        return query.order_by(column.desc())
