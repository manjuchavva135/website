from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from io import BytesIO
import re

from pypdf import PdfReader


def parse_decimal(value: str) -> Decimal | None:
    normalized = value.replace(",", "").strip()
    if not normalized:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", normalized)
    if not match:
        return None
    return Decimal(match.group(0))


def infer_fiscal_year(text: str, default_fy: str = "2025-26") -> str:
    match = re.search(r"(20\d{2})\s*[-/]\s*(\d{2,4})", text)
    if not match:
        return default_fy
    start = int(match.group(1))
    end_raw = match.group(2)
    end = int(end_raw if len(end_raw) == 4 else f"20{end_raw}")
    return f"{start}-{str(end)[-2:]}"


def fiscal_year_bounds(fiscal_year: str) -> tuple[date, date]:
    start_year = int(fiscal_year.split("-")[0])
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


def parse_month_period(month_label: str, default_year: int = 2025) -> tuple[date, date] | None:
    match = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(20\d{2})", month_label.lower())
    if match:
        mon = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(match.group(1)) + 1
        yr = int(match.group(2))
    else:
        mon_match = re.search(r"\b(1[0-2]|0?[1-9])\b", month_label)
        if not mon_match:
            return None
        mon = int(mon_match.group(1))
        yr = default_year
    last_day = monthrange(yr, mon)[1]
    return date(yr, mon, 1), date(yr, mon, last_day)


def extract_pdf_pages(payload: bytes) -> list[tuple[int, str]]:
    try:
        reader = PdfReader(BytesIO(payload))
        pages: list[tuple[int, str]] = []
        for index, page in enumerate(reader.pages, start=1):
            pages.append((index, page.extract_text() or ""))
        return pages
    except Exception:  # noqa: BLE001
        return [(1, payload.decode("utf-8", errors="ignore"))]


def extract_table_rows(page_text: str) -> list[tuple[int, list[str], str]]:
    rows: list[tuple[int, list[str], str]] = []
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for row_number, line in enumerate(lines, start=1):
        # Prefer direct table-like lines first.
        if "|" in line:
            parts = [part.strip() for part in line.split("|") if part.strip()]
            if len(parts) >= 2:
                rows.append((row_number, parts, "pipe"))
                continue
        # Fallback to fixed-width spacing found in many extracted PDFs.
        if re.search(r"\s{2,}", line):
            parts = [part.strip() for part in re.split(r"\s{2,}", line) if part.strip()]
            if len(parts) >= 2:
                rows.append((row_number, parts, "fixed"))
    return rows


def detect_authoritative_or_provisional_notes(text: str) -> list[str]:
    lowered = text.lower()
    notes: list[str] = []
    if "provisional" in lowered or "subject to audit" in lowered or "awaited" in lowered:
        notes.append("contains_provisional_or_awaited_disclosure")
    if "authoritative" in lowered or "finance accounts are authoritative" in lowered:
        notes.append("contains_authoritative_precedence_note")
    return notes
