from __future__ import annotations

import re
from dataclasses import replace
from io import BytesIO

from worker.rbi_ingestion.confidence import score_record_confidence
from worker.rbi_ingestion.extract_utils import compact_whitespace, parse_date, parse_decimal
from worker.rbi_ingestion.models import ParsedBorrowingRecord
from worker.rbi_ingestion.source_classifier import infer_event_type

try:
    from pypdf import PdfReader
except Exception:  # noqa: BLE001
    PdfReader = None

try:
    import pdfplumber
except Exception:  # noqa: BLE001
    pdfplumber = None


_AP_PATTERNS = (
    re.compile(r"\bandhra\s+pradesh\b", re.IGNORECASE),
    re.compile(r"\ba\.?\s*p\.?\s+sdl\b", re.IGNORECASE),
    re.compile(r"\b(?:gov(?:ernment)?\s+of\s+)?a\.?\s*p\.?\b", re.IGNORECASE),
)


def _is_ap_row(text: str) -> bool:
    """Return True if the given text mentions Andhra Pradesh in any common form."""
    if not text:
        return False
    return any(p.search(text) for p in _AP_PATTERNS)


def parse_borrowing_records_from_pdf(
    payload: bytes,
    source_url: str,
    source_family: str,
) -> list[ParsedBorrowingRecord]:
    """Extract AP-only borrowing records from an RBI SDL auction PDF.

    Tries pdfplumber table extraction first (handles structured auction
    tables), falls back to the line-based parser for free-text PDFs.
    """
    table_records = _parse_with_pdfplumber(payload, source_url, source_family)
    if table_records:
        return table_records
    return _parse_with_text(payload, source_url, source_family)


def _parse_with_pdfplumber(
    payload: bytes,
    source_url: str,
    source_family: str,
) -> list[ParsedBorrowingRecord]:
    if pdfplumber is None:
        return []
    records: list[ParsedBorrowingRecord] = []
    try:
        with pdfplumber.open(BytesIO(payload)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if not table:
                        continue
                    header = [_norm(c) for c in (table[0] or [])]
                    col = _column_index(header)
                    for raw_row in table[1:]:
                        if not raw_row:
                            continue
                        row_text = " | ".join(c or "" for c in raw_row)
                        if not _is_ap_row(row_text):
                            continue
                        rec = _row_to_record(raw_row, col, source_url, source_family)
                        if rec is not None:
                            records.append(rec)
    except Exception:  # noqa: BLE001
        return []
    return records


def _norm(value: object) -> str:
    return compact_whitespace(str(value or "")).lower()


def _column_index(header: list[str]) -> dict[str, int]:
    """Map known column names to their index in the table header."""
    aliases: dict[str, list[str]] = {
        "state": ["state", "issuer"],
        "notified": ["notified amount", "notified", "notified amount (rs crore)"],
        "accepted": ["accepted amount", "accepted", "accepted amount (rs crore)"],
        "tenor": ["tenor", "tenor (years)"],
        "yield": ["cut-off yield", "cutoff yield", "yield", "coupon"],
        "date": ["auction date", "settlement date", "date"],
        "maturity": ["maturity date", "maturity"],
        "issue": ["issue", "security", "series"],
    }
    out: dict[str, int] = {}
    for key, options in aliases.items():
        for idx, cell in enumerate(header):
            if any(opt in cell for opt in options):
                out[key] = idx
                break
    return out


def _row_to_record(
    raw_row: list[str | None],
    col: dict[str, int],
    source_url: str,
    source_family: str,
) -> ParsedBorrowingRecord | None:
    def cell(key: str) -> str:
        idx = col.get(key)
        if idx is None or idx >= len(raw_row):
            return ""
        return compact_whitespace(str(raw_row[idx] or ""))

    event_date = parse_date(cell("date"))
    if event_date is None:
        return None

    state = cell("state") or "Andhra Pradesh"
    if not _is_ap_row(state):
        # Header column may not have included state — best-effort allow if any cell mentions AP.
        if not any(_is_ap_row(str(c or "")) for c in raw_row):
            return None
        state = "Andhra Pradesh"

    issue_name = cell("issue") or "Andhra Pradesh SDL"
    record = ParsedBorrowingRecord(
        source_url=source_url,
        source_family=source_family,
        event_date=event_date,
        state="Andhra Pradesh",
        issue_name=issue_name,
        series=cell("issue") or None,
        notified_amount=parse_decimal(cell("notified")),
        accepted_amount=parse_decimal(cell("accepted")),
        underwriting_notified_amount=None,
        tenor=cell("tenor") or None,
        maturity_date=parse_date(cell("maturity")),
        coupon_or_cutoff_yield=parse_decimal(cell("yield")),
        event_type=infer_event_type(source_family=source_family, text_hint=issue_name),
        parser_confidence=0.0,
        notes=None,
    )
    return replace(record, parser_confidence=score_record_confidence(record))


def _parse_with_text(
    payload: bytes,
    source_url: str,
    source_family: str,
) -> list[ParsedBorrowingRecord]:
    text = _extract_text(payload)
    lines = [compact_whitespace(line) for line in text.splitlines() if compact_whitespace(line)]

    records: list[ParsedBorrowingRecord] = []
    for line in lines:
        date_candidate = _extract_first(line, ["date:", "auction date:", "date "])
        event_date = parse_date(date_candidate)
        if event_date is None:
            continue

        explicit_state = _extract_first(line, ["state:"])
        if explicit_state and not _is_ap_row(explicit_state):
            continue
        if not explicit_state and not _is_ap_row(line):
            # No state hint and no AP keyword anywhere in line — skip.
            continue

        issue_name = _extract_first(line, ["issue:", "series:", "security:"]) or "Andhra Pradesh SDL"

        record = ParsedBorrowingRecord(
            source_url=source_url,
            source_family=source_family,
            event_date=event_date,
            state="Andhra Pradesh",
            issue_name=issue_name,
            series=_extract_first(line, ["series:"]) or None,
            notified_amount=parse_decimal(_extract_first(line, ["notified amount:", "notified:"])),
            accepted_amount=parse_decimal(_extract_first(line, ["accepted amount:", "accepted:"])),
            underwriting_notified_amount=parse_decimal(_extract_first(line, ["underwriting notified:", "underwriting:"])),
            tenor=_extract_first(line, ["tenor:"]) or None,
            maturity_date=parse_date(_extract_first(line, ["maturity date:", "maturity:"])),
            coupon_or_cutoff_yield=parse_decimal(_extract_first(line, ["coupon:", "cut-off yield:", "yield:"])),
            event_type=infer_event_type(source_family=source_family, text_hint=line),
            parser_confidence=0.0,
            notes=None,
        )
        records.append(replace(record, parser_confidence=score_record_confidence(record)))
    return records


def _extract_text(payload: bytes) -> str:
    if PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(payload))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:  # noqa: BLE001
            return payload.decode("utf-8", errors="ignore")
    return payload.decode("utf-8", errors="ignore")


def _extract_first(line: str, labels: list[str]) -> str:
    lowered = line.lower()
    for label in labels:
        if label in lowered:
            start = lowered.index(label) + len(label)
            remainder = line[start:]
            delimiter_positions = [
                pos for pos in [remainder.find("|"), remainder.find(";")] if pos >= 0
            ]
            if delimiter_positions:
                return remainder[: min(delimiter_positions)].strip()
            return remainder.strip()
    return ""
