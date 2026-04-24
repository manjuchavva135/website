from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy.orm import Session

from app.models import ReviewAction, ReviewActionType, SourceDocument
from worker.ap_finance_ingestion.classifier import classify_ap_document_family
from worker.ap_finance_ingestion.fetcher import APFetchClient
from worker.ap_finance_ingestion.models import APFinanceSourceSpec
from worker.ap_finance_ingestion.parser import parse_html_document, parse_pdf_document
from worker.ap_finance_ingestion.persistence import APFinancePersistence
from worker.crawler.observability import get_crawler_logger, log_event


@dataclass(frozen=True, slots=True)
class APIngestionSummary:
    discovered_documents: int
    fiscal_metrics_written: int
    department_spending_written: int
    debt_events_written: int
    debt_positions_written: int
    warning_count: int
    manual_review_count: int


class APFinanceIngestionService:
    def __init__(
        self,
        *,
        fetch_client: APFetchClient | None = None,
    ) -> None:
        self.fetch_client = fetch_client or APFetchClient()
        self.logger = get_crawler_logger()

    def _create_manual_review(
        self,
        persistence: APFinancePersistence,
        session: Session,
        source_document: SourceDocument,
        reason: str,
    ) -> None:
        review = ReviewAction(
            id=persistence._next_pk(ReviewAction),
            entity_table="source_documents",
            entity_id=source_document.id,
            action_type=ReviewActionType.flag,
            actor_email="system@public-finance.local",
            comments=reason[:1000],
            source_document_id=source_document.id,
            review_status="needs_manual_review",
        )
        session.add(review)

    def run(self, session: Session, source_specs: list[APFinanceSourceSpec]) -> APIngestionSummary:
        persistence = APFinancePersistence(session)

        visited: set[str] = set()
        queue = list(source_specs)
        discovered_documents = 0
        fiscal_written = 0
        spending_written = 0
        debt_events_written = 0
        debt_positions_written = 0
        warning_count = 0
        manual_review_count = 0

        while queue:
            spec = queue.pop(0)
            if spec.url in visited:
                continue
            visited.add(spec.url)

            outcome = self.fetch_client.fetch(spec.url)
            doc = persistence.upsert_source_document(
                source_url=outcome.url,
                source_family=spec.source_family,
                payload=outcome.payload,
                content_type=outcome.content_type,
            )
            discovered_documents += 1

            if outcome.anti_bot_signals:
                manual_review_count += 1
                self._create_manual_review(persistence, session, doc, ", ".join(outcome.anti_bot_signals))
                continue

            source_family = classify_ap_document_family(outcome.url, spec.source_family)
            content_type = (outcome.content_type or "").lower()
            is_pdf = "pdf" in content_type or outcome.url.lower().endswith(".pdf")

            if is_pdf:
                fiscal, spending, debt_events, debt_positions, warnings = parse_pdf_document(
                    outcome.url,
                    outcome.payload,
                    source_family,
                )
                links: list[str] = []
            else:
                fiscal, spending, debt_events, debt_positions, warnings, links = parse_html_document(
                    outcome.url,
                    outcome.text,
                    source_family,
                )

            warning_count += len(warnings)

            for warning in warnings:
                log_event(
                    self.logger,
                    "ap_finance.reconciliation_warning",
                    section=warning.section,
                    expected_total=str(warning.expected_total),
                    computed_total=str(warning.computed_total),
                    message=warning.message,
                    source_url=outcome.url,
                )

            for rec in fiscal:
                persistence.upsert_fiscal_metric(doc, rec)
                fiscal_written += 1

            for rec in spending:
                persistence.upsert_department_spending(doc, rec)
                spending_written += 1

            for rec in debt_events:
                persistence.upsert_debt_event(doc, rec)
                debt_events_written += 1

            for rec in debt_positions:
                persistence.upsert_debt_position(doc, rec)
                debt_positions_written += 1

            for link in links:
                if link not in visited and any(link.lower().endswith(ext) for ext in [".pdf", ".html", ".htm"]):
                    queue.append(APFinanceSourceSpec(source_family=source_family, url=link))

            session.flush()

            log_event(
                self.logger,
                "ap_finance.ingested_document",
                source_url=outcome.url,
                source_family=source_family,
                checksum_sha256=sha256(outcome.payload).hexdigest(),
                fiscal_records=len(fiscal),
                spending_records=len(spending),
                debt_events=len(debt_events),
                debt_positions=len(debt_positions),
                warnings=len(warnings),
            )

        session.commit()
        return APIngestionSummary(
            discovered_documents=discovered_documents,
            fiscal_metrics_written=fiscal_written,
            department_spending_written=spending_written,
            debt_events_written=debt_events_written,
            debt_positions_written=debt_positions_written,
            warning_count=warning_count,
            manual_review_count=manual_review_count,
        )
