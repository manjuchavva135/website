from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BasisTag,
    DebtEvent,
    DebtEventType,
    DebtInstrument,
    DebtPosition,
    DepartmentSpending,
    FiscalMetric,
    ProvenanceLink,
    SourceDocument,
    SourceDocumentType,
    SourcePage,
)
from worker.ap_finance_ingestion.models import (
    ParsedDebtEventRecord,
    ParsedDebtPositionRecord,
    ParsedDepartmentSpendingRecord,
    ParsedFiscalMetricRecord,
)


class APFinancePersistence:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _next_pk(self, model: type) -> int | None:
        if self.session.bind is None or self.session.bind.dialect.name != "sqlite":
            return None
        current = self.session.execute(select(func.max(model.id))).scalar_one_or_none() or 0
        return int(current) + 1

    def upsert_source_document(
        self,
        *,
        source_url: str,
        source_family: str,
        payload: bytes,
        content_type: str | None,
    ) -> SourceDocument:
        checksum = sha256(payload).hexdigest()
        stmt = select(SourceDocument).where(
            SourceDocument.source_name == "ap_finance",
            SourceDocument.checksum_sha256 == checksum,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        storage_hash = sha256(source_url.encode("utf-8")).hexdigest()[:16]
        extension = "pdf" if (content_type or "").lower().find("pdf") >= 0 or source_url.lower().endswith(".pdf") else "html"
        document = SourceDocument(
            source_name="ap_finance",
            publisher="Government of Andhra Pradesh Finance Department",
            source_url=source_url,
            canonical_url=source_url,
            title=f"{source_family}:{source_url}",
            document_type=SourceDocumentType.pdf if extension == "pdf" else SourceDocumentType.html,
            mime_type=content_type,
            publication_date=datetime.now(UTC).date(),
            effective_date=None,
            fiscal_year_label=None,
            checksum_sha256=checksum,
            content_length_bytes=len(payload),
            storage_bucket="ingestion",
            storage_key=f"ap_finance/{source_family}/{storage_hash}.{extension}",
            parser_version="ap_finance_v1",
            review_status="pending",
            review_notes=None,
            is_active_version=True,
        )
        self.session.add(document)
        self.session.flush()
        return document

    def _ensure_source_page(self, document_id: int, page_number: int, page_text: str | None) -> SourcePage:
        stmt = select(SourcePage).where(
            SourcePage.source_document_id == document_id,
            SourcePage.page_number == page_number,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        page = SourcePage(
            id=self._next_pk(SourcePage),
            source_document_id=document_id,
            page_number=page_number,
            page_label=f"page_{page_number}",
            page_checksum_sha256=sha256((page_text or "").encode("utf-8")).hexdigest() if page_text else None,
            extracted_text=page_text,
            row_start=None,
            row_end=None,
        )
        self.session.add(page)
        self.session.flush()
        return page

    def _upsert_debt_instrument(self, code: str, name: str, issuer_name: str) -> DebtInstrument:
        stmt = select(DebtInstrument).where(
            DebtInstrument.source_system == "AP_FINANCE",
            DebtInstrument.instrument_code == code,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        instrument = DebtInstrument(
            id=self._next_pk(DebtInstrument),
            source_system="AP_FINANCE",
            instrument_code=code,
            isin=None,
            instrument_name=name,
            issuer_name=issuer_name,
            instrument_type="STATE_LOAN",
            currency="INR",
            coupon_rate=None,
            issue_date=None,
            maturity_date=None,
            is_active=True,
        )
        self.session.add(instrument)
        self.session.flush()
        return instrument

    def _link_provenance(
        self,
        *,
        source_document_id: int,
        source_page_id: int,
        target_table: str,
        target_id: int,
        row_number: int | None,
        row_label: str | None,
        quote: str | None,
    ) -> None:
        stmt = select(ProvenanceLink).where(
            ProvenanceLink.target_table == target_table,
            ProvenanceLink.target_id == target_id,
            ProvenanceLink.source_document_id == source_document_id,
            ProvenanceLink.source_page_id == source_page_id,
            ProvenanceLink.row_number == row_number,
            ProvenanceLink.column_name.is_(None),
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return

        link = ProvenanceLink(
            id=self._next_pk(ProvenanceLink),
            target_table=target_table,
            target_id=target_id,
            source_document_id=source_document_id,
            source_page_id=source_page_id,
            row_number=row_number,
            row_label=row_label,
            column_name=None,
            cell_ref=None,
            quoted_text=quote,
            parser_run_id=None,
            confidence_score=1.0,
            notes="ap_finance_ingestion",
        )
        self.session.add(link)
        self.session.flush()

    def upsert_fiscal_metric(self, source_document: SourceDocument, record: ParsedFiscalMetricRecord) -> FiscalMetric:
        stmt = select(FiscalMetric).where(
            FiscalMetric.metric_code == record.metric_code,
            FiscalMetric.period_start == record.period_start,
            FiscalMetric.period_end == record.period_end,
            FiscalMetric.basis_tag == BasisTag(record.basis_tag),
            FiscalMetric.department_code == record.department_code,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()

        if existing is not None:
            existing.metric_name = record.metric_name
            existing.metric_group = record.metric_group
            existing.fiscal_year = record.fiscal_year
            existing.value = record.value_inr_crore
            existing.unit = "INR crore"
            existing.notes = record.notes
            model = existing
        else:
            model = FiscalMetric(
                id=self._next_pk(FiscalMetric),
                metric_code=record.metric_code,
                metric_name=record.metric_name,
                metric_group=record.metric_group,
                basis_tag=BasisTag(record.basis_tag),
                fiscal_year=record.fiscal_year,
                period_start=record.period_start,
                period_end=record.period_end,
                value=record.value_inr_crore,
                unit="INR crore",
                department_code=record.department_code,
                notes=record.notes,
            )
            self.session.add(model)
            self.session.flush()

        page = self._ensure_source_page(source_document.id, record.provenance.page_number, record.provenance.quoted_text)
        self._link_provenance(
            source_document_id=source_document.id,
            source_page_id=page.id,
            target_table="fiscal_metrics",
            target_id=model.id,
            row_number=record.provenance.row_number,
            row_label=record.provenance.row_label,
            quote=record.provenance.quoted_text,
        )
        return model

    def upsert_department_spending(
        self,
        source_document: SourceDocument,
        record: ParsedDepartmentSpendingRecord,
    ) -> DepartmentSpending:
        stmt = select(DepartmentSpending).where(
            DepartmentSpending.department_code == record.department_code,
            DepartmentSpending.budget_head_id.is_(None),
            DepartmentSpending.period_start == record.period_start,
            DepartmentSpending.period_end == record.period_end,
            DepartmentSpending.basis_tag == BasisTag(record.basis_tag),
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            existing.department_name = record.department_name
            existing.spending_category = record.spending_category
            existing.fiscal_year = record.fiscal_year
            existing.amount = record.amount_inr_crore
            existing.unit = "INR crore"
            model = existing
        else:
            model = DepartmentSpending(
                id=self._next_pk(DepartmentSpending),
                department_code=record.department_code,
                department_name=record.department_name,
                budget_head_id=None,
                spending_category=record.spending_category,
                basis_tag=BasisTag(record.basis_tag),
                fiscal_year=record.fiscal_year,
                period_start=record.period_start,
                period_end=record.period_end,
                amount=record.amount_inr_crore,
                unit="INR crore",
            )
            self.session.add(model)
            self.session.flush()

        page = self._ensure_source_page(source_document.id, record.provenance.page_number, record.provenance.quoted_text)
        self._link_provenance(
            source_document_id=source_document.id,
            source_page_id=page.id,
            target_table="department_spending",
            target_id=model.id,
            row_number=record.provenance.row_number,
            row_label=record.provenance.row_label,
            quote=record.provenance.quoted_text,
        )
        return model

    def upsert_debt_event(self, source_document: SourceDocument, record: ParsedDebtEventRecord) -> DebtEvent:
        instrument = self._upsert_debt_instrument(record.instrument_code, record.instrument_name, record.issuer_name)
        stmt = select(DebtEvent).where(
            DebtEvent.debt_instrument_id == instrument.id,
            DebtEvent.event_type == DebtEventType(record.event_type),
            DebtEvent.event_date == record.event_date,
            DebtEvent.basis_tag == BasisTag(record.basis_tag),
            DebtEvent.amount == record.amount_inr_crore,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            existing.counterparty = record.issuer_name
            existing.notes = record.notes
            model = existing
        else:
            model = DebtEvent(
                id=self._next_pk(DebtEvent),
                debt_instrument_id=instrument.id,
                event_type=DebtEventType(record.event_type),
                event_date=record.event_date,
                basis_tag=BasisTag(record.basis_tag),
                amount=record.amount_inr_crore,
                units="INR crore",
                counterparty=record.issuer_name,
                notes=record.notes,
            )
            self.session.add(model)
            self.session.flush()

        page = self._ensure_source_page(source_document.id, record.provenance.page_number, record.provenance.quoted_text)
        self._link_provenance(
            source_document_id=source_document.id,
            source_page_id=page.id,
            target_table="debt_events",
            target_id=model.id,
            row_number=record.provenance.row_number,
            row_label=record.provenance.row_label,
            quote=record.provenance.quoted_text,
        )
        return model

    def upsert_debt_position(self, source_document: SourceDocument, record: ParsedDebtPositionRecord) -> DebtPosition:
        instrument = self._upsert_debt_instrument(record.instrument_code, record.instrument_name, record.issuer_name)
        stmt = select(DebtPosition).where(
            DebtPosition.debt_instrument_id == instrument.id,
            DebtPosition.as_of_date == record.as_of_date,
            DebtPosition.basis_tag == BasisTag(record.basis_tag),
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            existing.outstanding_principal = record.outstanding_principal_inr_crore
            existing.accrued_interest = record.accrued_interest_inr_crore
            existing.face_value = record.face_value_inr_crore
            existing.market_value = record.market_value_inr_crore
            model = existing
        else:
            model = DebtPosition(
                id=self._next_pk(DebtPosition),
                debt_instrument_id=instrument.id,
                as_of_date=record.as_of_date,
                basis_tag=BasisTag(record.basis_tag),
                outstanding_principal=record.outstanding_principal_inr_crore,
                accrued_interest=record.accrued_interest_inr_crore,
                face_value=record.face_value_inr_crore,
                market_value=record.market_value_inr_crore,
            )
            self.session.add(model)
            self.session.flush()

        page = self._ensure_source_page(source_document.id, record.provenance.page_number, record.provenance.quoted_text)
        self._link_provenance(
            source_document_id=source_document.id,
            source_page_id=page.id,
            target_table="debt_positions",
            target_id=model.id,
            row_number=record.provenance.row_number,
            row_label=record.provenance.row_label,
            quote=record.provenance.quoted_text,
        )
        return model
