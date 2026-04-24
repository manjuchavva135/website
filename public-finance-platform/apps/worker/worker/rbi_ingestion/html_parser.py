from __future__ import annotations

from dataclasses import replace
from html.parser import HTMLParser
from urllib.parse import urljoin

from worker.rbi_ingestion.confidence import score_record_confidence
from worker.rbi_ingestion.extract_utils import compact_whitespace, parse_date, parse_decimal
from worker.rbi_ingestion.models import ParsedBorrowingRecord
from worker.rbi_ingestion.source_classifier import infer_event_type


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.links: list[str] = []
        self._in_row = False
        self._in_cell = False
        self._current_row: list[str] = []
        self._cell_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower_tag = tag.lower()
        if lower_tag == "tr":
            self._in_row = True
            self._current_row = []
        elif lower_tag in {"td", "th"} and self._in_row:
            self._in_cell = True
            self._cell_chunks = []
        elif lower_tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        lower_tag = tag.lower()
        if lower_tag in {"td", "th"} and self._in_cell:
            self._in_cell = False
            self._current_row.append(compact_whitespace("".join(self._cell_chunks)))
        elif lower_tag == "tr" and self._in_row:
            self._in_row = False
            if self._current_row:
                self.rows.append(self._current_row)


def extract_pdf_links_from_html(html: str, base_url: str) -> list[str]:
    parser = _TableParser()
    parser.feed(html)

    links: list[str] = []
    seen: set[str] = set()
    for href in parser.links:
        absolute = urljoin(base_url, href)
        if ".pdf" not in absolute.lower():
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links


def parse_borrowing_records_from_html(
    html: str,
    source_url: str,
    source_family: str,
) -> list[ParsedBorrowingRecord]:
    parser = _TableParser()
    parser.feed(html)

    if not parser.rows:
        return []

    header = [value.lower() for value in parser.rows[0]]
    rows = parser.rows[1:] if any("date" in value for value in header) else parser.rows

    records: list[ParsedBorrowingRecord] = []
    for row in rows:
        if len(row) < 4:
            continue
        joined_row = " | ".join(row)
        event_date = parse_date(_pick_value(row, header, ["auction date", "date"]))
        if event_date is None:
            continue
        state = _pick_value(row, header, ["state"])
        issue_name = _pick_value(row, header, ["issue", "series", "security"])
        if not issue_name:
            continue

        record = ParsedBorrowingRecord(
            source_url=source_url,
            source_family=source_family,
            event_date=event_date,
            state=state or "Andhra Pradesh",
            issue_name=issue_name,
            series=_pick_value(row, header, ["series"]),
            notified_amount=parse_decimal(_pick_value(row, header, ["notified amount", "notified"])),
            accepted_amount=parse_decimal(_pick_value(row, header, ["accepted amount", "accepted"])),
            underwriting_notified_amount=parse_decimal(
                _pick_value(row, header, ["underwriting", "underwriting notified"])
            ),
            tenor=_pick_value(row, header, ["tenor"]),
            maturity_date=parse_date(_pick_value(row, header, ["maturity", "maturity date"])),
            coupon_or_cutoff_yield=parse_decimal(
                _pick_value(row, header, ["coupon", "cut-off yield", "cutoff yield", "yield"])
            ),
            event_type=infer_event_type(source_family=source_family, text_hint=joined_row),
            parser_confidence=0.0,
            notes=None,
        )
        scored = replace(record, parser_confidence=score_record_confidence(record))
        records.append(scored)
    return records


def _pick_value(row: list[str], header: list[str], labels: list[str]) -> str:
    for idx, name in enumerate(header):
        if any(label in name for label in labels) and idx < len(row):
            return row[idx]
    return ""
