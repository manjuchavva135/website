from pathlib import Path

from worker.rbi_ingestion.html_parser import extract_pdf_links_from_html, parse_borrowing_records_from_html
from worker.rbi_ingestion.pdf_parser import parse_borrowing_records_from_pdf


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "rbi"


def test_html_parser_extracts_records_and_links() -> None:
    html = (FIXTURE_DIR / "sdl_notification.html").read_text(encoding="utf-8")

    records = parse_borrowing_records_from_html(
        html,
        source_url="https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx",
        source_family="sdl_auction_notification",
    )
    links = extract_pdf_links_from_html(html, "https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx")

    assert len(records) == 1
    assert records[0].issue_name == "AP SDL 2036"
    assert records[0].event_type == "notified"
    assert records[0].parser_confidence >= 0.9
    assert links == ["https://www.rbi.org.in/Scripts/AP_SDL_Auction_Result_24042026.pdf"]


def test_pdf_parser_extracts_record() -> None:
    payload = (FIXTURE_DIR / "sdl_result.pdf").read_bytes()

    records = parse_borrowing_records_from_pdf(
        payload=payload,
        source_url="https://www.rbi.org.in/Scripts/AP_SDL_Auction_Result_24042026.pdf",
        source_family="sdl_auction_result",
    )

    assert len(records) == 1
    assert records[0].state == "Andhra Pradesh"
    assert str(records[0].accepted_amount) == "1920"
    assert records[0].event_type == "issued"
