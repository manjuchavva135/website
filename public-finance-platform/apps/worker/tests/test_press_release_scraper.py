"""Tests for the RBI press release listing parser. The actual HTTP path
is not exercised here; the scraper accepts pre-fetched HTML for testability.
"""

from __future__ import annotations

from datetime import date

from worker.rbi_ingestion.press_release_scraper import (
    AUCTION_KEYWORD,
    parse_press_release_listing,
)


_LISTING_HTML = """
<html>
  <body>
    <table>
      <tr>
        <td>Apr 24, 2026</td>
        <td><a href="/Scripts/AP_SDL_Auction_Result_24042026.pdf">
          Auction of State Government Securities — Apr 24, 2026
        </a></td>
      </tr>
      <tr>
        <td>Apr 17, 2026</td>
        <td><a href="/Scripts/Auction_17042026.pdf">
          Auction of State Government Securities, Andhra Pradesh
        </a></td>
      </tr>
      <tr>
        <td>Apr 18, 2026</td>
        <td><a href="/Scripts/PR_Other.aspx?Id=12345">
          RBI Monetary Policy Statement
        </a></td>
      </tr>
    </table>
  </body>
</html>
"""


def test_parser_filters_to_auction_titles() -> None:
    entries = parse_press_release_listing(_LISTING_HTML, base_url="https://rbi.org.in/")
    titles = [e.title for e in entries]
    assert all(AUCTION_KEYWORD.lower() in t.lower() for t in titles)
    assert len(entries) == 2


def test_parser_extracts_publication_date() -> None:
    entries = parse_press_release_listing(_LISTING_HTML, base_url="https://rbi.org.in/")
    by_url = {e.url: e for e in entries}
    apr24 = by_url["https://rbi.org.in/Scripts/AP_SDL_Auction_Result_24042026.pdf"]
    apr17 = by_url["https://rbi.org.in/Scripts/Auction_17042026.pdf"]
    assert apr24.publication_date == date(2026, 4, 24)
    assert apr17.publication_date == date(2026, 4, 17)


def test_parser_skips_non_auction_press_releases() -> None:
    entries = parse_press_release_listing(_LISTING_HTML, base_url="https://rbi.org.in/")
    assert all("monetary policy" not in e.title.lower() for e in entries)


def test_scraper_filters_by_since_date(monkeypatch) -> None:
    from worker.rbi_ingestion.press_release_scraper import RbiPressReleaseScraper

    scraper = RbiPressReleaseScraper(http_client=_StubClient())

    def _fake_download(url):  # noqa: ANN001
        return url, b"%PDF-1.4 fake"

    monkeypatch.setattr(scraper, "_download_pdf", _fake_download)

    fetched = scraper.get_new_auction_pdfs(since_date=date(2026, 4, 18), html=_LISTING_HTML)
    # Only Apr 24 is strictly after Apr 18.
    assert len(fetched) == 1
    assert fetched[0].publication_date == date(2026, 4, 24)


class _StubClient:
    def get(self, url):  # noqa: ANN001
        raise AssertionError("Network call not expected in this test")

    def close(self) -> None:  # pragma: no cover
        pass
