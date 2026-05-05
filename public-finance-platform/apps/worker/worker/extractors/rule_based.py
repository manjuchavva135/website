from __future__ import annotations

from worker.config import settings
from worker.extractors.base import ExtractionResult


class RuleBasedExtractor:
    """Dispatches to the existing deterministic parsers by source_family."""

    name = "rule_based"

    def extract(
        self,
        content: bytes,
        document_type: str,
        source_family: str,
        source_url: str = "",
    ) -> ExtractionResult:
        result = ExtractionResult(
            source_family=source_family,
            document_type=document_type,
            parser_name=self.name,
            parser_version=settings.parser_version,
        )

        if source_family == "rbi":
            self._extract_rbi(content, document_type, source_url, result)
        elif source_family == "ap_finance":
            self._extract_ap_finance(content, document_type, source_url, result)
        elif source_family in ("cag_annual", "cag_monthly", "cag"):
            self._extract_cag(content, document_type, source_family, source_url, result)
        else:
            # Unknown source: extract raw text pages as warnings for manual review.
            result.warnings.append(
                f"No rule-based parser for source_family='{source_family}'; "
                "raw text only — review manually."
            )
            if document_type == "pdf":
                result.warnings.extend(self._raw_pdf_pages(content))

        result.confidence = self._mean_confidence(result)
        return result

    # ------------------------------------------------------------------ #
    # Per-source dispatch                                                  #
    # ------------------------------------------------------------------ #

    def _extract_rbi(
        self, content: bytes, document_type: str, source_url: str, result: ExtractionResult
    ) -> None:
        if document_type == "pdf":
            from worker.rbi_ingestion.pdf_parser import parse_borrowing_records_from_pdf
            records = parse_borrowing_records_from_pdf(content, source_url, "rbi")
            result.borrowing_records.extend(records)
        elif document_type == "html":
            from worker.rbi_ingestion.html_parser import parse_borrowing_records_from_html
            records = parse_borrowing_records_from_html(
                content.decode("utf-8", errors="replace"), source_url, "rbi"
            )
            result.borrowing_records.extend(records)
        else:
            result.warnings.append(f"RBI: unsupported document_type '{document_type}'")

    def _extract_ap_finance(
        self, content: bytes, document_type: str, source_url: str, result: ExtractionResult
    ) -> None:
        from worker.ap_finance_ingestion.parser import parse_html_document, parse_pdf_document

        if document_type == "pdf":
            fiscal, spending, debt_events, debt_positions, warnings, _ = parse_pdf_document(
                source_url, content, "ap_finance"
            )
        elif document_type == "html":
            fiscal, spending, debt_events, debt_positions, warnings, _ = parse_html_document(
                source_url, content.decode("utf-8", errors="replace"), "ap_finance"
            )
        else:
            result.warnings.append(f"AP Finance: unsupported document_type '{document_type}'")
            return

        result.fiscal_metrics.extend(fiscal)
        result.department_spending.extend(spending)
        result.debt_events.extend(debt_events)
        result.debt_positions.extend(debt_positions)
        result.warnings.extend(w.message for w in warnings)

    def _extract_cag(
        self,
        content: bytes,
        document_type: str,
        source_family: str,
        source_url: str,
        result: ExtractionResult,
    ) -> None:
        from worker.cag_ingestion.classifier import classify_cag_document_family

        if document_type != "pdf":
            result.warnings.append(f"CAG: unsupported document_type '{document_type}'")
            return

        doc_family = classify_cag_document_family(source_url, b"")

        if doc_family == "monthly_key_indicators":
            from worker.cag_ingestion.monthly_parser import parse_cag_monthly_key_indicators
            parse_result = parse_cag_monthly_key_indicators(content, source_url)
        else:
            from worker.cag_ingestion.annual_parser import parse_cag_annual_accounts
            parse_result = parse_cag_annual_accounts(content, source_url)

        result.fiscal_metrics.extend(parse_result.fiscal_metrics)
        result.debt_positions.extend(parse_result.debt_positions)
        result.department_spending.extend(parse_result.department_spending)
        result.warnings.extend(parse_result.warnings)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _raw_pdf_pages(self, content: bytes) -> list[str]:
        try:
            from worker.cag_ingestion.extract_utils import extract_pdf_pages
            pages = extract_pdf_pages(content)
            return [f"Page {p}: {text[:200]}..." for p, text in pages if text.strip()]
        except Exception as exc:  # noqa: BLE001
            return [f"Could not extract PDF text: {exc}"]

    def _mean_confidence(self, result: ExtractionResult) -> float:
        all_records = (
            result.borrowing_records
            + result.fiscal_metrics
            + result.department_spending
            + result.debt_events
            + result.debt_positions
        )
        if not all_records:
            return 0.0
        scores = [
            getattr(r, "parser_confidence", None)
            for r in all_records
            if getattr(r, "parser_confidence", None) is not None
        ]
        return sum(scores) / len(scores) if scores else 0.0
