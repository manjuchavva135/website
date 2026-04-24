from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlsplit

from worker.crawler.canonicalization import canonicalize_url


@dataclass(frozen=True, slots=True)
class DiscoveredLink:
    url: str
    text: str


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[DiscoveredLink] = []
        self.page_title: str = ""
        self._href: str | None = None
        self._text_parts: list[str] = []
        self._inside_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag.lower() == "a":
            self._href = attrs_dict.get("href")
            self._text_parts = []
        elif tag.lower() == "title":
            self._inside_title = True

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name == "a" and self._href:
            text = " ".join(part.strip() for part in self._text_parts if part.strip()).strip()
            self.links.append(DiscoveredLink(url=self._href, text=text))
            self._href = None
            self._text_parts = []
        elif tag_name == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)
        if self._inside_title:
            self.page_title += data


def extract_page_title(html: str) -> str:
    parser = _AnchorParser()
    parser.feed(html)
    return parser.page_title.strip()


def extract_pdf_links(html: str, base_url: str) -> list[DiscoveredLink]:
    parser = _AnchorParser()
    parser.feed(html)

    seen: set[str] = set()
    pdf_links: list[DiscoveredLink] = []
    for link in parser.links:
        canonical_url = canonicalize_url(link.url, base_url=base_url)
        normalized = canonical_url.lower()
        if not _looks_like_pdf(normalized, link.text):
            continue
        if canonical_url in seen:
            continue
        seen.add(canonical_url)
        pdf_links.append(DiscoveredLink(url=canonical_url, text=link.text.strip()))
    return pdf_links


def _looks_like_pdf(url: str, link_text: str) -> bool:
    path = urlsplit(url).path.lower()
    lowered_text = link_text.lower()
    return path.endswith(".pdf") or ".pdf" in url or "pdf" in lowered_text