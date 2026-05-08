"""Scrape the RBI press release page for new SDL auction PDFs.

Filters press release rows to those whose title contains
"Auction of State Government Securities" and whose publication date is
strictly after the supplied ``since_date``. Downloads each matching PDF
and returns ``(title, publication_date, pdf_url, pdf_bytes)`` tuples.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

DEFAULT_PRESS_RELEASE_URL = (
    "https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
)
AUCTION_KEYWORD = "Auction of State Government Securities"

_DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%Y-%m-%d")


@dataclass(frozen=True, slots=True)
class PressReleaseEntry:
    title: str
    publication_date: date | None
    url: str


@dataclass(frozen=True, slots=True)
class FetchedAuctionPdf:
    title: str
    publication_date: date | None
    pdf_url: str
    pdf_bytes: bytes


class RbiPressReleaseScraper:
    def __init__(
        self,
        *,
        listing_url: str = DEFAULT_PRESS_RELEASE_URL,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 30.0,
        max_pdfs_per_run: int = 50,
    ) -> None:
        self.listing_url = listing_url
        self._client = http_client or httpx.Client(
            timeout=timeout_seconds, follow_redirects=True
        )
        self._owns_client = http_client is None
        self.max_pdfs_per_run = max_pdfs_per_run

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------ #

    def list_auction_entries(self, html: str | None = None) -> list[PressReleaseEntry]:
        if html is None:
            html = self._client.get(self.listing_url).raise_for_status().text
        return parse_press_release_listing(html, base_url=self.listing_url)

    def get_new_auction_pdfs(
        self, since_date: date, *, html: str | None = None
    ) -> list[FetchedAuctionPdf]:
        entries = self.list_auction_entries(html=html)
        new_entries = [
            e
            for e in entries
            if AUCTION_KEYWORD.lower() in e.title.lower()
            and (e.publication_date is None or e.publication_date > since_date)
        ]
        new_entries.sort(key=lambda e: e.publication_date or date.min)
        new_entries = new_entries[: self.max_pdfs_per_run]

        fetched: list[FetchedAuctionPdf] = []
        for entry in new_entries:
            pdf_url, pdf_bytes = self._download_pdf(entry.url)
            if pdf_bytes is None:
                continue
            fetched.append(
                FetchedAuctionPdf(
                    title=entry.title,
                    publication_date=entry.publication_date,
                    pdf_url=pdf_url or entry.url,
                    pdf_bytes=pdf_bytes,
                )
            )
        return fetched

    def _download_pdf(self, entry_url: str) -> tuple[str | None, bytes | None]:
        """Resolve an entry URL to the underlying SDL result PDF and download it.

        Some press-release entries link directly to a PDF; others point to an
        intermediate HTML page that contains the PDF link. Handles both.
        """
        try:
            resp = self._client.get(entry_url)
            resp.raise_for_status()
        except httpx.HTTPError:
            return None, None

        content_type = resp.headers.get("content-type", "").lower()
        if "pdf" in content_type or entry_url.lower().endswith(".pdf"):
            return entry_url, resp.content

        # Look for a PDF link inside the HTML body.
        pdf_url = _first_pdf_link(resp.text, base_url=entry_url)
        if not pdf_url:
            return None, None
        try:
            pdf_resp = self._client.get(pdf_url)
            pdf_resp.raise_for_status()
        except httpx.HTTPError:
            return pdf_url, None
        return pdf_url, pdf_resp.content


# ---------------------------------------------------------------------- #
# Pure helpers (BeautifulSoup) — separated for unit-testability.         #
# ---------------------------------------------------------------------- #


def parse_press_release_listing(
    html: str, *, base_url: str = DEFAULT_PRESS_RELEASE_URL
) -> list[PressReleaseEntry]:
    """Extract press-release entries from the RBI listing page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    entries: list[PressReleaseEntry] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a"):
        title = anchor.get_text(strip=True)
        href = anchor.get("href", "")
        if not title or not href:
            continue
        if AUCTION_KEYWORD.lower() not in title.lower():
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen_urls:
            continue
        pub = _publication_date_for_anchor(anchor)
        entries.append(PressReleaseEntry(title=title, publication_date=pub, url=absolute))
        seen_urls.add(absolute)
    return entries


def _publication_date_for_anchor(anchor) -> date | None:  # noqa: ANN001
    """Look near the anchor (parent / siblings) for a date string."""
    candidates: list[str] = []
    parent = anchor.parent
    if parent is not None:
        candidates.append(parent.get_text(" ", strip=True))
    grandparent = parent.parent if parent is not None else None
    if grandparent is not None:
        candidates.append(grandparent.get_text(" ", strip=True))
    for text in candidates:
        parsed = _parse_date(text)
        if parsed is not None:
            return parsed
    return None


def _parse_date(text: str) -> date | None:
    if not text:
        return None
    # Try a sliding window across common date patterns.
    for match in re.finditer(
        r"\b\d{1,2}[\s\-/][A-Za-z]+[\s\-/]\d{2,4}\b|\b[A-Za-z]+\s+\d{1,2},\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b",
        text,
    ):
        candidate = match.group(0)
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    return None


def _first_pdf_link(html: str, *, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a"):
        href = anchor.get("href", "")
        if href and href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    return None
