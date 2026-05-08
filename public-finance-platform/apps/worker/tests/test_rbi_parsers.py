from pathlib import Path

from worker.rbi_ingestion.pdf_parser import parse_borrowing_records_from_pdf


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "rbi"


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
