from __future__ import annotations

from worker.config import settings
from worker.extractors.base import ExtractionResult


class RuleBasedExtractor:
    """Dispatches to the deterministic parsers by source_family.

    Supported families:
      - rbi_auction         : RBI SDL auction PDFs (filtered to Andhra Pradesh rows)
      - outstanding_securities : RBI outstanding state-securities PDFs (AP only)
      - ap_budget           : Andhra Pradesh budget volume PDFs
    """

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

        if source_family in ("rbi_auction", "rbi", "sdl_auction_result", "sdl_auction_notification"):
            self._extract_rbi_auction(content, document_type, source_url, result)
        elif source_family == "outstanding_securities":
            self._extract_outstanding(content, document_type, source_url, result)
        elif source_family == "ap_budget":
            self._extract_ap_budget(content, document_type, source_url, result)
        else:
            result.warnings.append(
                f"No rule-based parser for source_family='{source_family}'; "
                "raw text only — review manually."
            )

        result.confidence = self._mean_confidence(result)
        return result

    # ------------------------------------------------------------------ #

    def _extract_rbi_auction(
        self, content: bytes, document_type: str, source_url: str, result: ExtractionResult
    ) -> None:
        if document_type != "pdf":
            result.warnings.append(f"RBI auction: unsupported document_type '{document_type}'")
            return
        from worker.rbi_ingestion.pdf_parser import parse_borrowing_records_from_pdf
        records = parse_borrowing_records_from_pdf(content, source_url, "rbi_auction")
        result.borrowing_records.extend(records)

    def _extract_outstanding(
        self, content: bytes, document_type: str, source_url: str, result: ExtractionResult
    ) -> None:
        if document_type != "pdf":
            result.warnings.append(f"Outstanding securities: unsupported document_type '{document_type}'")
            return
        # Phase 2 fills this in.
        try:
            from worker.rbi_ingestion.outstanding_parser import parse_outstanding_securities_bytes
        except ImportError:
            result.warnings.append("outstanding_parser not yet implemented (Phase 2)")
            return
        positions = parse_outstanding_securities_bytes(content, source_url)
        result.debt_positions.extend(positions)

    def _extract_ap_budget(
        self, content: bytes, document_type: str, source_url: str, result: ExtractionResult
    ) -> None:
        if document_type != "pdf":
            result.warnings.append(f"AP Budget: unsupported document_type '{document_type}'")
            return
        # Phase 5 fills this in.
        try:
            from worker.ap_budget.budget_parser import parse_budget_bytes
        except ImportError:
            result.warnings.append("ap_budget parser not yet implemented (Phase 5)")
            return
        fiscal, spending = parse_budget_bytes(content, source_url)
        result.fiscal_metrics.extend(fiscal)
        result.department_spending.extend(spending)

    # ------------------------------------------------------------------ #

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
