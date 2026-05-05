from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class ExtractionResult:
    """Unified output from any extractor implementation."""

    source_family: str
    document_type: str  # pdf | html | xlsx | csv | other
    parser_name: str
    parser_version: str

    # Per-source record lists — only the relevant ones are populated.
    borrowing_records: list = field(default_factory=list)   # ParsedBorrowingRecord
    fiscal_metrics: list = field(default_factory=list)      # ParsedFiscalMetricRecord / ParsedCAGFiscalMetric
    department_spending: list = field(default_factory=list) # ParsedDepartmentSpendingRecord / ParsedCAGDepartmentSpending
    debt_events: list = field(default_factory=list)         # ParsedDebtEventRecord
    debt_positions: list = field(default_factory=list)      # ParsedDebtPositionRecord / ParsedCAGDebtPosition

    warnings: list[str] = field(default_factory=list)
    confidence: float = 0.0  # mean confidence across all extracted rows


@runtime_checkable
class ExtractorProvider(Protocol):
    """Protocol that every extractor implementation must satisfy."""

    def extract(
        self,
        content: bytes,
        document_type: str,
        source_family: str,
        source_url: str = "",
    ) -> ExtractionResult: ...
