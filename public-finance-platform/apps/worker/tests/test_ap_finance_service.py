from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import ReviewAction
from worker.ap_finance_ingestion.fetcher import FetchOutcome
from worker.ap_finance_ingestion.models import APFinanceSourceSpec
from worker.ap_finance_ingestion.service import APFinanceIngestionService


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ap_finance"


class StubFetcher:
    def __init__(self, responses: dict[str, FetchOutcome]) -> None:
        self.responses = responses

    def fetch(self, url: str) -> FetchOutcome:
        return self.responses[url]


def test_service_creates_manual_review_on_anti_bot() -> None:
    anti_bot_html = "<html><body>captcha required</body></html>"
    service = APFinanceIngestionService(
        fetch_client=StubFetcher(
            {
                "https://finance.ap.gov.in/budget.html": FetchOutcome(
                    url="https://finance.ap.gov.in/budget.html",
                    status_code=200,
                    payload=anti_bot_html.encode("utf-8"),
                    text=anti_bot_html,
                    content_type="text/html",
                    anti_bot_signals=["body:captcha"],
                )
            }
        )
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionFactory() as session:
        summary = service.run(
            session,
            [APFinanceSourceSpec(source_family="budget_in_brief", url="https://finance.ap.gov.in/budget.html")],
        )

        assert summary.manual_review_count == 1
        assert session.query(ReviewAction).count() == 1


def test_service_persists_parsed_records() -> None:
    html = (FIXTURE_DIR / "budget_summary.html").read_text(encoding="utf-8")
    service = APFinanceIngestionService(
        fetch_client=StubFetcher(
            {
                "https://finance.ap.gov.in/budget.html": FetchOutcome(
                    url="https://finance.ap.gov.in/budget.html",
                    status_code=200,
                    payload=html.encode("utf-8"),
                    text=html,
                    content_type="text/html",
                    anti_bot_signals=[],
                )
            }
        )
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionFactory() as session:
        summary = service.run(
            session,
            [APFinanceSourceSpec(source_family="budget_in_brief", url="https://finance.ap.gov.in/budget.html")],
        )

        assert summary.fiscal_metrics_written >= 1
        assert summary.department_spending_written >= 1
