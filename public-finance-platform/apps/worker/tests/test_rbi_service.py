from pathlib import Path

import httpx

from worker.rbi_ingestion.fetcher import FetchOutcome
from worker.rbi_ingestion.models import RbiSourceSpec
from worker.rbi_ingestion.service import RbiBorrowingIngestionService


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "rbi"


class StubFetcher:
    def __init__(self, responses: dict[str, FetchOutcome]) -> None:
        self.responses = responses

    def fetch(self, url: str) -> FetchOutcome:
        return self.responses[url]


class StubPersistence:
    def __init__(self) -> None:
        self.upserts = 0
        self.manual_reviews = 0
        self.context_records = 0

    def upsert_borrowing_record(self, record):
        self.upserts += 1
        return 1, self.upserts, True

    def create_manual_review_task(self, source_url: str, source_family: str, reason: str):
        self.manual_reviews += 1
        return self.manual_reviews

    def create_source_context_record(self, source_url: str, source_family: str, note: str):
        self.context_records += 1
        return self.context_records


def test_service_skips_broken_or_non_pdf_links_without_failing_task() -> None:
    html = """
    <html>
      <body>
        <a href="https://www.fbil.org.in/uploads/general/FBIL-SDL_Valuation_Methodology.pdf">FBIL</a>
        <a href="https://rbidocs.rbi.org.in/rdocs/content/pdfs/ANNEX20082019_1.pdf">RBI docs</a>
      </body>
    </html>
    """
    fetcher = FailingPdfFetcher(
        {
            "https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=3337": FetchOutcome(
                url="https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=3337",
                status_code=200,
                payload=html.encode("utf-8"),
                text=html,
                content_type="text/html",
                anti_bot_signals=[],
            ),
            "https://rbidocs.rbi.org.in/rdocs/content/pdfs/ANNEX20082019_1.pdf": FetchOutcome(
                url="https://rbidocs.rbi.org.in/rdocs/content/pdfs/ANNEX20082019_1.pdf",
                status_code=200,
                payload=b"<!DOCTYPE html><html><body>not a pdf</body></html>",
                text="<!DOCTYPE html><html><body>not a pdf</body></html>",
                content_type="text/html",
                anti_bot_signals=[],
            ),
        }
    )
    persistence = StubPersistence()
    service = RbiBorrowingIngestionService(
        fetch_client=fetcher,
        persistence=persistence,
        source_specs=[
            RbiSourceSpec(
                source_family="framework",
                url="https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=3337",
            )
        ],
    )

    result = service.run()

    assert result["status"] == "ok"
    assert result["sources"][0]["records_parsed"] == 0
    assert result["metrics"]["fetch_failures"] == 2
    assert persistence.context_records == 1


class FailingPdfFetcher(StubFetcher):
    def fetch(self, url: str) -> FetchOutcome:
        if url == "https://www.fbil.org.in/uploads/general/FBIL-SDL_Valuation_Methodology.pdf":
            raise httpx.HTTPStatusError(
                "Client error '404 Not Found' for url 'https://www.fbil.org.in/uploads/general/FBIL-SDL_Valuation_Methodology.pdf'",
                request=httpx.Request("GET", url),
                response=httpx.Response(404, request=httpx.Request("GET", url)),
            )
        return super().fetch(url)


def test_service_creates_manual_review_when_anti_bot_detected() -> None:
    anti_bot_html = (FIXTURE_DIR / "anti_bot.html").read_text(encoding="utf-8")
    fetcher = StubFetcher(
        {
            "https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx": FetchOutcome(
                url="https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx",
                status_code=200,
                payload=anti_bot_html.encode("utf-8"),
                text=anti_bot_html,
                content_type="text/html",
                anti_bot_signals=["body:captcha"],
            )
        }
    )
    persistence = StubPersistence()
    service = RbiBorrowingIngestionService(
        fetch_client=fetcher,
        persistence=persistence,
        source_specs=[
            RbiSourceSpec(
                source_family="sdl_auction_result",
                url="https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx",
            )
        ],
    )

    result = service.run()

    assert result["metrics"]["manual_review_tasks"] == 1
    assert persistence.manual_reviews == 1
    assert persistence.upserts == 0


def test_service_stores_wma_context_when_no_structured_rows() -> None:
    html = "<html><head><title>Ways and Means Advances framework</title></head><body>WMA policy page.</body></html>"
    fetcher = StubFetcher(
        {
            "https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=711": FetchOutcome(
                url="https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=711",
                status_code=200,
                payload=html.encode("utf-8"),
                text=html,
                content_type="text/html",
                anti_bot_signals=[],
            )
        }
    )
    persistence = StubPersistence()
    service = RbiBorrowingIngestionService(
        fetch_client=fetcher,
        persistence=persistence,
        source_specs=[
            RbiSourceSpec(
                source_family="wma_od",
                url="https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=711",
            )
        ],
    )

    result = service.run()

    assert result["metrics"]["source_context_records"] == 1
    assert persistence.context_records == 1
    assert persistence.upserts == 0
