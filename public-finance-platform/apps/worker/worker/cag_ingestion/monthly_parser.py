from __future__ import annotations

from dataclasses import replace

from worker.cag_ingestion.basis_rules import assign_basis_tag
from worker.cag_ingestion.classifier import classify_cag_document_family
from worker.cag_ingestion.confidence import score_fiscal_metric
from worker.cag_ingestion.extract_utils import (
    detect_authoritative_or_provisional_notes,
    extract_pdf_pages,
    extract_table_rows,
    infer_fiscal_year,
    parse_decimal,
    parse_month_period,
)
from worker.cag_ingestion.models import CAGDocumentParseResult, ParsedCAGFiscalMetric, ProvenanceLocator


def parse_cag_monthly_key_indicators(
    *,
    payload: bytes,
    source_url: str,
    page_title: str = "",
    anchor_text: str = "",
) -> CAGDocumentParseResult:
    family = classify_cag_document_family(source_url, page_title=page_title, anchor_text=anchor_text)
    basis_tag = assign_basis_tag(family)
    pages = extract_pdf_pages(payload)
    full_text = "\n".join(text for _, text in pages)

    fiscal_year = infer_fiscal_year(full_text)
    result = CAGDocumentParseResult(document_family=family)
    result.parser_notes.extend(detect_authoritative_or_provisional_notes(full_text))

    found_any = False
    for page_number, page_text in pages:
        for row_number, parts, _ in extract_table_rows(page_text):
            if len(parts) < 3:
                continue
            month_label = parts[0]
            metric_label = parts[1]
            amount = parse_decimal(parts[-1])
            if amount is None:
                continue
            month_period = parse_month_period(month_label)
            if month_period is None:
                continue
            period_start, period_end = month_period

            lower_metric = metric_label.lower()
            if not any(token in lower_metric for token in {"receipt", "expenditure", "deficit"}):
                continue
            found_any = True

            metric = ParsedCAGFiscalMetric(
                metric_code="mki_" + "".join(ch for ch in lower_metric if ch.isalnum())[:24],
                metric_name=metric_label,
                metric_group="monthly_key_indicators",
                basis_tag=basis_tag,
                fiscal_year=fiscal_year,
                period_start=period_start,
                period_end=period_end,
                value_inr_crore=amount,
                unit="INR crore",
                department_code=None,
                notes="monthly provisional indicator",
                parser_confidence=1.0,
                provenance=ProvenanceLocator(
                    source_url=source_url,
                    page_number=page_number,
                    row_number=row_number,
                    row_label=metric_label,
                    quoted_text=" | ".join(parts),
                    table_id=f"page_{page_number}",
                ),
            )
            result.fiscal_metrics.append(replace(metric, parser_confidence=score_fiscal_metric(metric)))

    if not found_any:
        result.missing_or_awaited_fields.append("missing_monthly_key_indicator_series")

    return result
