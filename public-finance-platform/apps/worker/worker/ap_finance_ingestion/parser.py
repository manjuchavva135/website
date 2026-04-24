from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
import re
from typing import Iterable

from bs4 import BeautifulSoup
from pypdf import PdfReader

from worker.ap_finance_ingestion.basis_rules import map_basis_tag
from worker.ap_finance_ingestion.confidence import (
    score_debt_event,
    score_debt_position,
    score_department_spending,
    score_fiscal_metric,
)
from worker.ap_finance_ingestion.models import (
    ParsedDebtEventRecord,
    ParsedDebtPositionRecord,
    ParsedDepartmentSpendingRecord,
    ParsedFiscalMetricRecord,
    ProvenanceLocator,
    ReconciliationWarning,
)
from worker.ap_finance_ingestion.reconciliation import detect_total_mismatch
from worker.ap_finance_ingestion.units import detect_unit_label, normalize_to_crore, parse_number


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


def _department_code(name: str) -> str:
    letters = [ch for ch in name.lower() if ch.isalnum()]
    return "dept_" + "".join(letters[:20])


def _metric_code(name: str) -> str:
    letters = [ch for ch in name.lower() if ch.isalnum()]
    return "fm_" + "".join(letters[:28])


def _extract_links_from_html(html_text: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    links: list[str] = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        if not href:
            continue
        if href.lower().startswith("http://") or href.lower().startswith("https://"):
            links.append(href)
        else:
            if base_url.endswith("/"):
                links.append(base_url + href.lstrip("/"))
            else:
                links.append(base_url.rsplit("/", 1)[0] + "/" + href.lstrip("/"))
    return links


def parse_html_document(url: str, html_text: str, source_family: str) -> tuple[
    list[ParsedFiscalMetricRecord],
    list[ParsedDepartmentSpendingRecord],
    list[ParsedDebtEventRecord],
    list[ParsedDebtPositionRecord],
    list[ReconciliationWarning],
    list[str],
]:
    soup = BeautifulSoup(html_text, "html.parser")
    fiscal: list[ParsedFiscalMetricRecord] = []
    spending: list[ParsedDepartmentSpendingRecord] = []
    debt_events: list[ParsedDebtEventRecord] = []
    debt_positions: list[ParsedDebtPositionRecord] = []
    warnings: list[ReconciliationWarning] = []
    discovered_links = _extract_links_from_html(html_text, url)

    title = (soup.title.string if soup.title and soup.title.string else "")
    fiscal_year = infer_fiscal_year(f"{title} {html_text[:1000]}")
    period_start, period_end = fiscal_year_bounds(fiscal_year)
    unit = detect_unit_label(html_text)
    basis_tag = map_basis_tag(title, source_family)

    for table in soup.select("table"):
        rows = table.select("tr")
        if not rows:
            continue

        header_cells = [cell.get_text(" ", strip=True).lower() for cell in rows[0].select("th,td")]
        section_amounts: list[Decimal] = []
        expected_total: Decimal | None = None

        for row_index, row in enumerate(rows[1:], start=2):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("th,td")]
            if len(cells) < 2:
                continue
            label = cells[0]
            amount_raw = cells[-1]
            parsed = parse_number(amount_raw)
            if parsed is None:
                continue
            amount_crore = normalize_to_crore(parsed, unit)
            lower_label = label.lower()

            prov = ProvenanceLocator(
                source_url=url,
                page_number=1,
                row_number=row_index,
                row_label=label,
                quoted_text=" | ".join(cells),
            )

            if "department" in " ".join(header_cells) or "grant" in " ".join(header_cells):
                if "total" in lower_label:
                    expected_total = amount_crore
                    continue
                spending_category = "revenue"
                if "capital" in lower_label:
                    spending_category = "capital"
                record = ParsedDepartmentSpendingRecord(
                    department_code=_department_code(label),
                    department_name=label,
                    spending_category=spending_category,
                    basis_tag=basis_tag,
                    fiscal_year=fiscal_year,
                    period_start=period_start,
                    period_end=period_end,
                    amount_inr_crore=amount_crore,
                    unit=unit,
                    source_family=source_family,
                    parser_confidence=1.0,
                    notes=None,
                    provenance=prov,
                )
                scored = replace(record, parser_confidence=score_department_spending(record))
                spending.append(scored)
                section_amounts.append(amount_crore)
                continue

            if any(token in lower_label for token in {"open market loan", "oml", "market borrowing"}):
                debt_event = ParsedDebtEventRecord(
                    instrument_code="ap_oml",
                    instrument_name="Open Market Loans",
                    issuer_name="Government of Andhra Pradesh",
                    event_type="issue",
                    basis_tag=basis_tag,
                    event_date=period_end,
                    amount_inr_crore=amount_crore,
                    coupon_or_yield=None,
                    maturity_date=None,
                    tenor=None,
                    source_family=source_family,
                    parser_confidence=1.0,
                    notes=None,
                    provenance=prov,
                )
                debt_event = replace(debt_event, parser_confidence=score_debt_event(debt_event))
                debt_events.append(debt_event)
                continue

            if any(token in lower_label for token in {"outstanding debt", "total debt outstanding", "public debt outstanding"}):
                debt_position = ParsedDebtPositionRecord(
                    instrument_code="ap_total_debt",
                    instrument_name="Total Debt Outstanding",
                    issuer_name="Government of Andhra Pradesh",
                    as_of_date=period_end,
                    basis_tag=basis_tag,
                    outstanding_principal_inr_crore=amount_crore,
                    accrued_interest_inr_crore=None,
                    face_value_inr_crore=None,
                    market_value_inr_crore=None,
                    source_family=source_family,
                    parser_confidence=1.0,
                    notes=None,
                    provenance=prov,
                )
                debt_position = replace(debt_position, parser_confidence=score_debt_position(debt_position))
                debt_positions.append(debt_position)
                continue

            if "total" in lower_label:
                expected_total = amount_crore
                continue

            metric = ParsedFiscalMetricRecord(
                metric_code=_metric_code(label),
                metric_name=label,
                metric_group="finance_summary",
                basis_tag=basis_tag,
                fiscal_year=fiscal_year,
                period_start=period_start,
                period_end=period_end,
                value_inr_crore=amount_crore,
                unit=unit,
                department_code=None,
                source_family=source_family,
                parser_confidence=1.0,
                notes=None,
                provenance=prov,
            )
            metric = replace(metric, parser_confidence=score_fiscal_metric(metric))
            fiscal.append(metric)
            section_amounts.append(amount_crore)

        warning = detect_total_mismatch("table_section", section_amounts, expected_total)
        if warning is not None:
            warnings.append(warning)

    return fiscal, spending, debt_events, debt_positions, warnings, discovered_links


def _iter_pdf_text_by_page(payload: bytes) -> Iterable[tuple[int, str]]:
    try:
        reader = PdfReader(BytesIO(payload))
    except Exception:  # noqa: BLE001
        return
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        yield page_number, text


def parse_pdf_document(url: str, payload: bytes, source_family: str) -> tuple[
    list[ParsedFiscalMetricRecord],
    list[ParsedDepartmentSpendingRecord],
    list[ParsedDebtEventRecord],
    list[ParsedDebtPositionRecord],
    list[ReconciliationWarning],
]:
    fiscal: list[ParsedFiscalMetricRecord] = []
    spending: list[ParsedDepartmentSpendingRecord] = []
    debt_events: list[ParsedDebtEventRecord] = []
    debt_positions: list[ParsedDebtPositionRecord] = []
    warnings: list[ReconciliationWarning] = []

    combined = ""
    for _, text in _iter_pdf_text_by_page(payload):
        combined += text + "\n"

    fiscal_year = infer_fiscal_year(combined)
    period_start, period_end = fiscal_year_bounds(fiscal_year)
    unit = detect_unit_label(combined)
    basis_tag = map_basis_tag(combined[:300], source_family)

    lines_by_page = list(_iter_pdf_text_by_page(payload))
    for page_number, page_text in lines_by_page:
        lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
        section_amounts: list[Decimal] = []
        expected_total: Decimal | None = None

        for row_number, line in enumerate(lines, start=1):
            amount = parse_number(line)
            if amount is None:
                continue
            amount_crore = normalize_to_crore(amount, unit)
            prov = ProvenanceLocator(
                source_url=url,
                page_number=page_number,
                row_number=row_number,
                row_label=line[:120],
                quoted_text=line,
            )
            lower_line = line.lower()

            if "department" in lower_line and amount_crore is not None:
                record = ParsedDepartmentSpendingRecord(
                    department_code=_department_code(line),
                    department_name=line,
                    spending_category="revenue",
                    basis_tag=basis_tag,
                    fiscal_year=fiscal_year,
                    period_start=period_start,
                    period_end=period_end,
                    amount_inr_crore=amount_crore,
                    unit=unit,
                    source_family=source_family,
                    parser_confidence=1.0,
                    notes=None,
                    provenance=prov,
                )
                record = replace(record, parser_confidence=score_department_spending(record))
                spending.append(record)
                section_amounts.append(amount_crore)
                continue

            if "open market loan" in lower_line:
                debt_event = ParsedDebtEventRecord(
                    instrument_code="ap_oml",
                    instrument_name="Open Market Loans",
                    issuer_name="Government of Andhra Pradesh",
                    event_type="issue",
                    basis_tag=basis_tag,
                    event_date=period_end,
                    amount_inr_crore=amount_crore,
                    coupon_or_yield=None,
                    maturity_date=None,
                    tenor=None,
                    source_family=source_family,
                    parser_confidence=1.0,
                    notes=None,
                    provenance=prov,
                )
                debt_event = replace(debt_event, parser_confidence=score_debt_event(debt_event))
                debt_events.append(debt_event)
                continue

            if "outstanding" in lower_line and "debt" in lower_line:
                debt_position = ParsedDebtPositionRecord(
                    instrument_code="ap_total_debt",
                    instrument_name="Total Debt Outstanding",
                    issuer_name="Government of Andhra Pradesh",
                    as_of_date=period_end,
                    basis_tag=basis_tag,
                    outstanding_principal_inr_crore=amount_crore,
                    accrued_interest_inr_crore=None,
                    face_value_inr_crore=None,
                    market_value_inr_crore=None,
                    source_family=source_family,
                    parser_confidence=1.0,
                    notes=None,
                    provenance=prov,
                )
                debt_position = replace(debt_position, parser_confidence=score_debt_position(debt_position))
                debt_positions.append(debt_position)
                continue

            if "total" in lower_line:
                expected_total = amount_crore
                continue

            metric = ParsedFiscalMetricRecord(
                metric_code=_metric_code(line),
                metric_name=line,
                metric_group="finance_summary",
                basis_tag=basis_tag,
                fiscal_year=fiscal_year,
                period_start=period_start,
                period_end=period_end,
                value_inr_crore=amount_crore,
                unit=unit,
                department_code=None,
                source_family=source_family,
                parser_confidence=1.0,
                notes=None,
                provenance=prov,
            )
            metric = replace(metric, parser_confidence=score_fiscal_metric(metric))
            fiscal.append(metric)
            section_amounts.append(amount_crore)

        warning = detect_total_mismatch(f"page_{page_number}", section_amounts, expected_total)
        if warning is not None:
            warnings.append(warning)

    return fiscal, spending, debt_events, debt_positions, warnings
