from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol

import httpx

from worker.crawler.canonicalization import canonicalize_url
from worker.crawler.classifier import classify_document_family
from worker.crawler.detection import detect_anti_bot_signals
from worker.crawler.extractors import DiscoveredLink, extract_page_title, extract_pdf_links
from worker.crawler.observability import CrawlMetrics, get_crawler_logger, log_event
from worker.crawler.persistence import FetchRunRecord, SourceDocumentRecord, SourcePersistenceService
from worker.crawler.registry import SourceRegistry, SourceRegistryEntry
from worker.crawler.storage import RawArtifactStorage


class HttpClient(Protocol):
    def get(
        self,
        url: str,
        *,
        timeout: float,
        follow_redirects: bool,
        headers: dict[str, str],
    ) -> httpx.Response: ...


class SourceDiscoveryCrawler:
    def __init__(
        self,
        registry: SourceRegistry,
        repository: SourcePersistenceService,
        storage: RawArtifactStorage,
        http_client: HttpClient,
        parser_version: str,
        request_timeout: float = 30.0,
    ) -> None:
        self.registry = registry
        self.repository = repository
        self.storage = storage
        self.http_client = http_client
        self.parser_version = parser_version
        self.request_timeout = request_timeout
        self.metrics = CrawlMetrics()
        self.logger = get_crawler_logger()

    def crawl_all(self) -> dict[str, object]:
        self.storage.ensure_bucket()
        source_results: list[dict[str, object]] = []
        for entry in self.registry.list_entries():
            source_results.append(self._crawl_entry(entry))
        return {
            "status": "ok",
            "sources_processed": len(source_results),
            "sources": source_results,
            "metrics": self.metrics.to_dict(),
        }

    def _crawl_entry(self, entry: SourceRegistryEntry) -> dict[str, object]:
        requested_url = canonicalize_url(entry.entrypoint_url)
        summary: dict[str, object] = {
            "source": entry.source_name,
            "entrypoint_url": requested_url,
            "documents": [],
        }
        seen_urls = {requested_url}

        try:
            response = self._fetch(requested_url)
        except Exception as exc:  # noqa: BLE001
            self._record_fetch_failure(entry=entry, requested_url=requested_url, error_message=str(exc))
            summary["error"] = str(exc)
            return summary

        page_title = extract_page_title(response.text)
        html_result = self._persist_response(
            entry=entry,
            requested_url=requested_url,
            response=response,
            display_title=page_title or entry.source_name,
            anchor_text=page_title,
            page_title=page_title,
            family_hint=entry.family_hint,
        )
        summary["documents"].append(html_result)

        if html_result["needs_manual_review"]:
            return summary

        discovered_links = extract_pdf_links(response.text, str(response.url))
        self.metrics.linked_pdfs_discovered += len(discovered_links)
        log_event(
            self.logger,
            "discovered_pdf_links",
            source=entry.source_name,
            count=len(discovered_links),
            entrypoint_url=requested_url,
        )

        for link in discovered_links:
            if link.url in seen_urls:
                continue
            seen_urls.add(link.url)

            try:
                pdf_response = self._fetch(link.url)
            except Exception as exc:  # noqa: BLE001
                self._record_fetch_failure(entry=entry, requested_url=link.url, error_message=str(exc))
                continue

            document_result = self._persist_response(
                entry=entry,
                requested_url=link.url,
                response=pdf_response,
                display_title=link.text or _basename(link.url),
                anchor_text=link.text,
                page_title=page_title,
                family_hint=entry.family_hint,
            )
            summary["documents"].append(document_result)

        return summary

    def _fetch(self, url: str) -> httpx.Response:
        log_event(self.logger, "fetch_started", url=url)
        response = self.http_client.get(
            url,
            timeout=self.request_timeout,
            follow_redirects=True,
            headers={"User-Agent": "public-finance-platform/1.0"},
        )
        response.raise_for_status()
        self.metrics.pages_fetched += 1
        return response

    def _persist_response(
        self,
        *,
        entry: SourceRegistryEntry,
        requested_url: str,
        response: httpx.Response,
        display_title: str,
        anchor_text: str,
        page_title: str,
        family_hint: str,
    ) -> dict[str, object]:
        resolved_url = canonicalize_url(str(response.url))
        checksum_sha256 = hashlib.sha256(response.content).hexdigest()
        content_type = response.headers.get("content-type")
        document_type = _infer_document_type(resolved_url=resolved_url, content_type=content_type)
        document_family = classify_document_family(
            resolved_url,
            anchor_text=anchor_text,
            page_title=page_title,
            family_hint=family_hint,
        )

        anti_bot_signals = detect_anti_bot_signals(
            html=response.text if document_type == "html" else "",
            headers=dict(response.headers.items()),
            status_code=response.status_code,
        )
        needs_manual_review = bool(anti_bot_signals)

        stored_document = self.repository.find_document_by_checksum(checksum_sha256)
        uploaded = False
        if stored_document is None:
            storage_key = self.storage.store_artifact(
                source_name=entry.source_name,
                document_family=document_family,
                checksum_sha256=checksum_sha256,
                source_url=resolved_url,
                payload=response.content,
                content_type=content_type,
            )
            uploaded = True
            review_status = "needs_manual_review" if needs_manual_review else "pending"
            review_notes = (
                "; ".join(anti_bot_signals)
                if needs_manual_review
                else f"document_family={document_family}"
            )
            document_id = self.repository.create_source_document(
                SourceDocumentRecord(
                    source_name=entry.source_name,
                    publisher=entry.publisher,
                    source_url=resolved_url,
                    canonical_url=resolved_url,
                    title=display_title[:500],
                    document_type=document_type,
                    mime_type=content_type,
                    publication_date=datetime.now(UTC).date(),
                    checksum_sha256=checksum_sha256,
                    content_length_bytes=len(response.content),
                    storage_bucket=self.storage.bucket_name,
                    storage_key=storage_key,
                    fetch_etag=response.headers.get("etag"),
                    parser_version=self.parser_version,
                    review_status=review_status,
                    review_notes=review_notes,
                )
            )
            self.metrics.documents_created += 1
            if uploaded:
                self.metrics.raw_uploads += 1
            if needs_manual_review:
                self.metrics.manual_review_documents += 1
        else:
            document_id = stored_document.id
            storage_key = stored_document.storage_key
            self.metrics.duplicate_documents += 1

        run_status = "partial" if needs_manual_review else "succeeded"
        self.repository.record_fetch_run(
            FetchRunRecord(
                source_name=entry.source_name,
                requested_url=requested_url,
                resolved_url=resolved_url,
                http_status_code=response.status_code,
                status=run_status,
                fetched_checksum_sha256=checksum_sha256,
                response_headers=dict(response.headers.items()),
                error_message="; ".join(anti_bot_signals) if anti_bot_signals else None,
                source_document_id=document_id,
            )
        )

        log_event(
            self.logger,
            "fetch_completed",
            checksum_sha256=checksum_sha256,
            document_family=document_family,
            document_id=document_id,
            document_type=document_type,
            needs_manual_review=needs_manual_review,
            requested_url=requested_url,
            resolved_url=resolved_url,
            source=entry.source_name,
            uploaded=uploaded,
        )

        return {
            "document_id": document_id,
            "document_family": document_family,
            "document_type": document_type,
            "needs_manual_review": needs_manual_review,
            "resolved_url": resolved_url,
            "storage_key": storage_key,
        }

    def _record_fetch_failure(self, *, entry: SourceRegistryEntry, requested_url: str, error_message: str) -> None:
        self.metrics.fetch_failures += 1
        self.repository.record_fetch_run(
            FetchRunRecord(
                source_name=entry.source_name,
                requested_url=requested_url,
                resolved_url=requested_url,
                http_status_code=None,
                status="failed",
                fetched_checksum_sha256=None,
                response_headers={},
                error_message=error_message[:2000],
                source_document_id=None,
            )
        )
        log_event(
            self.logger,
            "fetch_failed",
            error_message=error_message[:2000],
            requested_url=requested_url,
            source=entry.source_name,
        )


def _infer_document_type(resolved_url: str, content_type: str | None) -> str:
    lowered_content_type = (content_type or "").lower()
    if resolved_url.lower().endswith(".pdf") or "pdf" in lowered_content_type:
        return "pdf"
    if resolved_url.lower().endswith(".json") or "json" in lowered_content_type:
        return "json"
    if resolved_url.lower().endswith(".csv") or "csv" in lowered_content_type:
        return "csv"
    return "html"


def _basename(url: str) -> str:
    return url.rsplit("/", maxsplit=1)[-1] or url