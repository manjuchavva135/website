from __future__ import annotations

from worker.rbi_ingestion.fetcher import FetchClient
from worker.rbi_ingestion.html_parser import extract_pdf_links_from_html, parse_borrowing_records_from_html
from worker.rbi_ingestion.logging_metrics import RbiIngestionMetrics, emit_pipeline_event
from worker.rbi_ingestion.models import ParsedBorrowingRecord, RbiSourceSpec
from worker.rbi_ingestion.pdf_parser import parse_borrowing_records_from_pdf
from worker.rbi_ingestion.persistence import RbiPersistence
from worker.rbi_ingestion.source_classifier import classify_rbi_source_family


class RbiBorrowingIngestionService:
    def __init__(
        self,
        fetch_client: FetchClient,
        persistence: RbiPersistence,
        source_specs: list[RbiSourceSpec],
    ) -> None:
        self.fetch_client = fetch_client
        self.persistence = persistence
        self.source_specs = source_specs
        self.metrics = RbiIngestionMetrics()

    def run(self) -> dict[str, object]:
        outputs: list[dict[str, object]] = []
        for spec in self.source_specs:
            outputs.append(self._process_source(spec))
        return {
            "status": "ok",
            "sources_processed": len(outputs),
            "sources": outputs,
            "metrics": self.metrics.to_dict(),
        }

    def _process_source(self, spec: RbiSourceSpec) -> dict[str, object]:
        emit_pipeline_event("rbi_source_started", url=spec.url, source_family=spec.source_family)
        try:
            outcome = self.fetch_client.fetch(spec.url)
            self.metrics.pages_fetched += 1
        except Exception as exc:  # noqa: BLE001
            self.metrics.fetch_failures += 1
            emit_pipeline_event("rbi_source_fetch_failed", url=spec.url, error=str(exc))
            return {"url": spec.url, "error": str(exc)}

        if outcome.anti_bot_signals:
            self.metrics.manual_review_tasks += 1
            self.persistence.create_manual_review_task(
                source_url=spec.url,
                source_family=spec.source_family,
                reason="; ".join(outcome.anti_bot_signals),
            )
            emit_pipeline_event(
                "rbi_source_requires_manual_review",
                url=spec.url,
                signals=outcome.anti_bot_signals,
            )
            return {
                "url": spec.url,
                "manual_review": True,
                "signals": outcome.anti_bot_signals,
            }

        source_family = spec.source_family or classify_rbi_source_family(spec.url)
        records = parse_borrowing_records_from_html(outcome.text, source_url=outcome.url, source_family=source_family)

        pdf_links = extract_pdf_links_from_html(outcome.text, base_url=outcome.url)
        for link in pdf_links:
            pdf_outcome = self.fetch_client.fetch(link)
            self.metrics.pdfs_fetched += 1
            records.extend(
                parse_borrowing_records_from_pdf(
                    payload=pdf_outcome.payload,
                    source_url=pdf_outcome.url,
                    source_family=classify_rbi_source_family(pdf_outcome.url),
                )
            )

        if not records and source_family in {"wma_od", "framework"}:
            self.persistence.create_source_context_record(
                source_url=outcome.url,
                source_family=source_family,
                note="No structured auction rows; stored as contextual cash-management reference",
            )
            self.metrics.source_context_records += 1
            emit_pipeline_event(
                "rbi_context_record_stored",
                url=outcome.url,
                source_family=source_family,
            )

        parsed = self._persist_records(records)
        emit_pipeline_event(
            "rbi_source_completed",
            url=spec.url,
            source_family=spec.source_family,
            records=len(records),
            parsed=parsed,
        )
        return {
            "url": spec.url,
            "records_parsed": len(records),
            "records_persisted": parsed,
        }

    def _persist_records(self, records: list[ParsedBorrowingRecord]) -> int:
        persisted = 0
        for record in records:
            _, _, created = self.persistence.upsert_borrowing_record(record)
            self.metrics.records_parsed += 1
            self.metrics.instruments_upserted += 1
            if created:
                self.metrics.events_upserted += 1
            else:
                self.metrics.duplicate_events += 1
            persisted += 1
        return persisted
