from __future__ import annotations

import httpx

from worker.crawler import (
    FetchRunRecord,
    SourceDiscoveryCrawler,
    SourceRegistry,
    SourceRegistryEntry,
    StoredDocument,
    classify_document_family,
    detect_anti_bot_page,
    extract_pdf_links,
)


class FakeHttpClient:
    def __init__(self, responses: dict[str, httpx.Response]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(
        self,
        url: str,
        *,
        timeout: float,
        follow_redirects: bool,
        headers: dict[str, str],
    ) -> httpx.Response:
        self.calls.append(url)
        return self.responses[url]


class FakeStorage:
    def __init__(self) -> None:
        self.bucket_name = "test-bucket"
        self.uploads: list[dict[str, str]] = []

    def ensure_bucket(self) -> None:
        return None

    def store_artifact(
        self,
        source_name: str,
        document_family: str,
        checksum_sha256: str,
        source_url: str,
        payload: bytes,
        content_type: str | None,
    ) -> str:
        storage_key = f"raw/{source_name}/{document_family}/{checksum_sha256}"
        self.uploads.append(
            {
                "source_name": source_name,
                "document_family": document_family,
                "checksum_sha256": checksum_sha256,
                "source_url": source_url,
                "storage_key": storage_key,
            }
        )
        return storage_key


class FakeRepository:
    def __init__(self) -> None:
        self.documents_by_checksum: dict[str, StoredDocument] = {}
        self.documents_created: list[object] = []
        self.fetch_runs: list[FetchRunRecord] = []

    def find_document_by_checksum(self, checksum_sha256: str) -> StoredDocument | None:
        return self.documents_by_checksum.get(checksum_sha256)

    def create_source_document(self, record: object) -> int:
        document_id = len(self.documents_created) + 1
        checksum_sha256 = getattr(record, "checksum_sha256")
        storage_key = getattr(record, "storage_key")
        self.documents_created.append(record)
        self.documents_by_checksum[checksum_sha256] = StoredDocument(
            id=document_id,
            checksum_sha256=checksum_sha256,
            storage_key=storage_key,
        )
        return document_id

    def record_fetch_run(self, record: FetchRunRecord) -> int:
        self.fetch_runs.append(record)
        return len(self.fetch_runs)


def test_extract_pdf_links_canonicalizes_and_deduplicates() -> None:
    html = """
    <html>
      <body>
        <a href="/docs/Budget-2025.pdf?utm_source=newsletter&b=2&a=1#fragment">Budget 2025 PDF</a>
        <a href="https://apfinance.gov.in/docs/Budget-2025.pdf?a=1&b=2">Duplicate budget pdf</a>
        <a href="/docs/overview.html">Overview</a>
      </body>
    </html>
    """

    links = extract_pdf_links(html, "https://apfinance.gov.in/budget.html")

    assert links == [
        type(links[0])(
            url="https://apfinance.gov.in/docs/Budget-2025.pdf?a=1&b=2",
            text="Budget 2025 PDF",
        )
    ]


def test_classification_rules_cover_core_families() -> None:
    assert classify_document_family("https://apfinance.gov.in/docs/frbm-report-2025.pdf") == "frbm_report"
    assert classify_document_family("https://apfinance.gov.in/docs/budget-speech.pdf") == "budget"
    assert classify_document_family("https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx") == "press_release"
    assert classify_document_family("https://cag.gov.in/en/state-accounts-report?defuat_state_id=64") == "state_accounts"


def test_detect_anti_bot_pages() -> None:
    html = "<html><title>Just a moment...</title><body>Please complete the CAPTCHA challenge.</body></html>"
    assert detect_anti_bot_page(html, headers={"cf-ray": "abc"}, status_code=403) is True
    assert detect_anti_bot_page("<html><body>Budget documents</body></html>", headers={}, status_code=200) is False


def test_checksum_deduplication_skips_duplicate_pdf_uploads() -> None:
    seed_entry = SourceRegistryEntry(
        source_name="ap_budget",
        publisher="Andhra Pradesh Finance Department",
        entrypoint_url="https://apfinance.gov.in/budget.html",
        family_hint="budget",
    )
    registry = SourceRegistry(entries=[seed_entry])

    html_payload = b"""
    <html>
      <head><title>Budget Documents</title></head>
      <body>
        <a href="https://apfinance.gov.in/docs/budget-volume-1.pdf">Volume 1</a>
        <a href="https://apfinance.gov.in/docs/budget-volume-1-copy.pdf">Volume 1 Copy</a>
      </body>
    </html>
    """
    pdf_payload = b"%PDF-1.4 duplicate-budget-payload"

    http_client = FakeHttpClient(
        responses={
            "https://apfinance.gov.in/budget.html": httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                content=html_payload,
                request=httpx.Request("GET", "https://apfinance.gov.in/budget.html"),
            ),
            "https://apfinance.gov.in/docs/budget-volume-1.pdf": httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=pdf_payload,
                request=httpx.Request("GET", "https://apfinance.gov.in/docs/budget-volume-1.pdf"),
            ),
            "https://apfinance.gov.in/docs/budget-volume-1-copy.pdf": httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=pdf_payload,
                request=httpx.Request("GET", "https://apfinance.gov.in/docs/budget-volume-1-copy.pdf"),
            ),
        }
    )
    repository = FakeRepository()
    storage = FakeStorage()
    crawler = SourceDiscoveryCrawler(
        registry=registry,
        repository=repository,
        storage=storage,
        http_client=http_client,
        parser_version="2026.04.24",
    )

    result = crawler.crawl_all()

    assert result["metrics"]["duplicate_documents"] == 1
    assert len(storage.uploads) == 2
    assert len(repository.documents_created) == 2
    assert len(repository.fetch_runs) == 3