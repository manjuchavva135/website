from __future__ import annotations

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


def parse_borrowing_records_from_pdf(
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

        issue_name = _extract_first(line, ["issue:", "series:", "security:"])
        if not issue_name:
            issue_name = "Andhra Pradesh SDL"

        record = ParsedBorrowingRecord(
            source_url=source_url,
            source_family=source_family,
            event_date=event_date,
            state=_extract_first(line, ["state:"]) or "Andhra Pradesh",
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
