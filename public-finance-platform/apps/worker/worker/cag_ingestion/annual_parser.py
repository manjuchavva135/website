from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from worker.cag_ingestion.basis_rules import assign_basis_tag
from worker.cag_ingestion.classifier import classify_cag_document_family
from worker.cag_ingestion.confidence import score_debt_position, score_department_spending, score_fiscal_metric
from worker.cag_ingestion.extract_utils import (
    detect_authoritative_or_provisional_notes,
    extract_pdf_pages,
    extract_table_rows,
    fiscal_year_bounds,
    infer_fiscal_year,
    parse_decimal,
)
from worker.cag_ingestion.models import (
    CAGDocumentParseResult,
    ParsedCAGDebtPosition,
    ParsedCAGDepartmentSpending,
    ParsedCAGFiscalMetric,
    ProvenanceLocator,
)


def _metric_code(label: str) -> str:
    safe = "".join(ch for ch in label.lower() if ch.isalnum())[:28]
    return f"cag_{safe}"


def _dept_code(label: str) -> str:
    safe = "".join(ch for ch in label.lower() if ch.isalnum())[:20]
    return f"grant_{safe}"


def _try_add_core_fiscal_metric(
    result: CAGDocumentParseResult,
    *,
    label: str,
    value: Decimal,
    basis_tag: str,
    fiscal_year: str,
    period_start,
    period_end,
    source_url: str,
    page_number: int,
    row_number: int,
    quote: str,
    metric_group: str,
) -> None:
    metric = ParsedCAGFiscalMetric(
        metric_code=_metric_code(label),
        metric_name=label,
        metric_group=metric_group,
        basis_tag=basis_tag,
        fiscal_year=fiscal_year,
        period_start=period_start,
        period_end=period_end,
        value_inr_crore=value,
        unit="INR crore",
        department_code=None,
        notes=None,
        parser_confidence=1.0,
        provenance=ProvenanceLocator(
            source_url=source_url,
            page_number=page_number,
            row_number=row_number,
            row_label=label,
            quoted_text=quote,
            table_id=f"page_{page_number}",
        ),
    )
    result.fiscal_metrics.append(replace(metric, parser_confidence=score_fiscal_metric(metric)))


def parse_cag_annual_accounts(
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
    period_start, period_end = fiscal_year_bounds(fiscal_year)
    result = CAGDocumentParseResult(document_family=family)
    result.parser_notes.extend(detect_authoritative_or_provisional_notes(full_text))

    expected_metric_flags = {
        "receipts": False,
        "expenditure": False,
        "deficit": False,
        "public_account": False,
        "total_liabilities": False,
    }
    found_debt = False
    found_spending = False

    for page_number, page_text in pages:
        rows = extract_table_rows(page_text)
        for row_number, parts, _ in rows:
            label = parts[0].strip()
            amount = parse_decimal(parts[-1])
            if amount is None:
                continue
            lower = label.lower()
            quote = " | ".join(parts)

            if "receipt" in lower:
                expected_metric_flags["receipts"] = True
                _try_add_core_fiscal_metric(
                    result,
                    label="Audited Receipts",
                    value=amount,
                    basis_tag=basis_tag,
                    fiscal_year=fiscal_year,
                    period_start=period_start,
                    period_end=period_end,
                    source_url=source_url,
                    page_number=page_number,
                    row_number=row_number,
                    quote=quote,
                    metric_group="receipts",
                )
                continue

            if "expenditure" in lower and "grant" not in lower and "appropriation" not in lower:
                expected_metric_flags["expenditure"] = True
                _try_add_core_fiscal_metric(
                    result,
                    label="Audited Expenditure",
                    value=amount,
                    basis_tag=basis_tag,
                    fiscal_year=fiscal_year,
                    period_start=period_start,
                    period_end=period_end,
                    source_url=source_url,
                    page_number=page_number,
                    row_number=row_number,
                    quote=quote,
                    metric_group="expenditure",
                )
                continue

            if "deficit" in lower:
                expected_metric_flags["deficit"] = True
                _try_add_core_fiscal_metric(
                    result,
                    label=label,
                    value=amount,
                    basis_tag=basis_tag,
                    fiscal_year=fiscal_year,
                    period_start=period_start,
                    period_end=period_end,
                    source_url=source_url,
                    page_number=page_number,
                    row_number=row_number,
                    quote=quote,
                    metric_group="deficit",
                )
                continue

            if "public account" in lower:
                expected_metric_flags["public_account"] = True
                _try_add_core_fiscal_metric(
                    result,
                    label="Public Account",
                    value=amount,
                    basis_tag=basis_tag,
                    fiscal_year=fiscal_year,
                    period_start=period_start,
                    period_end=period_end,
                    source_url=source_url,
                    page_number=page_number,
                    row_number=row_number,
                    quote=quote,
                    metric_group="public_account",
                )
                continue

            if "liabilities" in lower:
                expected_metric_flags["total_liabilities"] = True
                _try_add_core_fiscal_metric(
                    result,
                    label="Total Liabilities",
                    value=amount,
                    basis_tag=basis_tag,
                    fiscal_year=fiscal_year,
                    period_start=period_start,
                    period_end=period_end,
                    source_url=source_url,
                    page_number=page_number,
                    row_number=row_number,
                    quote=quote,
                    metric_group="liabilities",
                )
                continue

            if "public debt" in lower or "debt" in lower:
                found_debt = True
                debt = ParsedCAGDebtPosition(
                    instrument_code="cag_public_debt_total",
                    instrument_name="Public Debt Total",
                    issuer_name="Government of Andhra Pradesh",
                    as_of_date=period_end,
                    basis_tag=basis_tag,
                    outstanding_principal_inr_crore=amount,
                    accrued_interest_inr_crore=None,
                    face_value_inr_crore=None,
                    market_value_inr_crore=None,
                    notes=None,
                    parser_confidence=1.0,
                    provenance=ProvenanceLocator(
                        source_url=source_url,
                        page_number=page_number,
                        row_number=row_number,
                        row_label=label,
                        quoted_text=quote,
                        table_id=f"page_{page_number}",
                    ),
                )
                result.debt_positions.append(replace(debt, parser_confidence=score_debt_position(debt)))
                continue

            if "grant" in lower or "appropriation" in lower:
                found_spending = True
                spending_category = "appropriation_actual_expenditure"
                if "saving" in lower:
                    spending_category = "appropriation_savings"
                spending = ParsedCAGDepartmentSpending(
                    department_code=_dept_code(label),
                    department_name=label,
                    spending_category=spending_category,
                    basis_tag=basis_tag,
                    fiscal_year=fiscal_year,
                    period_start=period_start,
                    period_end=period_end,
                    amount_inr_crore=amount,
                    unit="INR crore",
                    notes=None,
                    parser_confidence=1.0,
                    provenance=ProvenanceLocator(
                        source_url=source_url,
                        page_number=page_number,
                        row_number=row_number,
                        row_label=label,
                        quoted_text=quote,
                        table_id=f"page_{page_number}",
                    ),
                )
                result.department_spending.append(replace(spending, parser_confidence=score_department_spending(spending)))

    for key, found in expected_metric_flags.items():
        if not found:
            result.missing_or_awaited_fields.append(f"missing_{key}")

    if not found_debt:
        result.missing_or_awaited_fields.append("missing_public_debt")
    if not found_spending:
        result.missing_or_awaited_fields.append("missing_grant_or_appropriation_spending")

    return result
