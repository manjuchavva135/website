"""Dispatch each xlsx file in the dataset to its statement-specific parser."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from app.models import RunStatus
from worker.state_finances_xlsx.persist import (
    IngestStats,
    finish_parser_run,
    get_or_create_source_document,
    open_session,
    persist_debt_instruments,
    persist_fiscal_metrics,
    start_parser_run,
)
from worker.state_finances_xlsx.records import DebtInstrumentRow, FiscalMetricRow

log = logging.getLogger(__name__)

ParserFunc = Callable[[Path], Iterable[FiscalMetricRow | DebtInstrumentRow]]

# (lowercase filename) -> (title, parser module under worker.state_finances_xlsx.parsers)
_REGISTRY: dict[str, tuple[str, str]] = {
    # --- Phase 1.5 high-priority debt statements ---
    "total_outstanding_liabilities_of_state-governments.xlsx": (
        "RBI Statement 19 — Total Outstanding Liabilities of State Governments",
        "total_outstanding_liabilities",
    ),
    "total_outstanding_liabilities-as_percent_of_gsdp.xlsx": (
        "RBI Statement 20 — Total Outstanding Liabilities as % of GSDP",
        "total_outstanding_liabilities_pct_gsdp",
    ),
    "composition_of_outstanding_liabilities.xlsx": (
        "RBI Statement 18 — Composition of Outstanding Liabilities",
        "composition_outstanding_liabilities",
    ),
    "market_borrowings_of_state_governments.xlsx": (
        "RBI Statement 21 — Market Borrowings of State Governments",
        "market_borrowings",
    ),
    "maturity_profile-of_outstanding_state_goverment_securities.xlsx": (
        "RBI Statement 23 — Maturity Profile of Outstanding State Government Securities (₹ Cr)",
        "maturity_profile_value",
    ),
    "maturity_profile_of_outstanding-state_government-securities_as_percent-of_total.xlsx": (
        "RBI Statement 24 — Maturity Profile as % of Total",
        "maturity_profile_pct",
    ),
    "outstanding_guarntees_of_state_governments.xlsx": (
        "RBI Statement 28 — Outstanding Guarantees of State Governments",
        "guarantees",
    ),
    # --- Phase 1.6 per-instrument SDL ---
    "outstanding_government-securities_asof_may-06-2026.xls": (
        "RBI Outstanding State Government Securities — as of 6 May 2026",
        "outstanding_securities_per_instrument",
    ),
    # --- Phase 1.7: deficits, interest, receipts, expenditure (added incrementally) ---
    "major_fisical_indicators.xlsx": (
        "RBI Statement 1 — Major Fiscal Indicators",
        "major_fiscal_indicators",
    ),
    "revenue_deficit_and_surplus.xlsx": (
        "RBI Statement 2 — Revenue Deficit / Surplus",
        "revenue_deficit_surplus",
    ),
    "gross_fiscal_deficit_and_surplus.xlsx": (
        "RBI Statement 3 — Gross Fiscal Deficit / Surplus",
        "gross_fiscal_deficit_surplus",
    ),
    "interest_payments.xlsx": (
        "RBI Statement 13 — Interest Payments",
        "interest_payments",
    ),
    "loans_from_center.xlsx": (
        "RBI Statement 16 — Loans from the Centre",
        "loans_from_centre",
    ),
    "tax_revenue.xlsx": (
        "RBI Statement 14 — Tax Revenue",
        "tax_revenue",
    ),
    "non-tax_revenue.xlsx": (
        "RBI Statement 15 — Non-Tax Revenue",
        "non_tax_revenue",
    ),
    "devolution_and_transfer_of_resources_from_centre.xlsx": (
        "RBI Statement 17 — Devolution and Transfer of Resources from the Centre",
        "devolution_transfers",
    ),
    "developmental_expenditure.xlsx": (
        "RBI Statement 11 — Development Expenditure",
        "developmental_expenditure",
    ),
    "non-developmental_expenditure.xlsx": (
        "RBI Statement 12 — Non-Development Expenditure",
        "non_developmental_expenditure",
    ),
    "expenditure_on_wages_and_salaries.xlsx": (
        "RBI Statement 29 — Expenditure on Wages and Salaries",
        "wages_salaries",
    ),
    "expenditure_on-operations-and_maintainance.xlsx": (
        "RBI Statement 30 — Expenditure on Operations and Maintenance",
        "operations_maintenance",
    ),
    "social-sector-expenditure.xlsx": (
        "RBI Statement 31 — Social Sector Expenditure",
        "social_sector_expenditure",
    ),
    "social_sector-expenditure-as_percent_of_total_disbursement.xlsx": (
        "RBI Statement 32 — Social Sector Expenditure as % of Total Disbursement",
        "social_sector_expenditure_pct",
    ),
    "expenditure_on-education-as_percent_of_aggregate_expenditure.xlsx": (
        "RBI Statement 26 — Education as % of Aggregate Expenditure",
        "education_expenditure_pct",
    ),
    "expenditure_on_medical-and-public_health-and_family-welfare_as_percent-of_aggregate_expenditure.xlsx": (
        "RBI Statement 27 — Health as % of Aggregate Expenditure",
        "health_expenditure_pct",
    ),
}


def _resolve_parser(module_name: str) -> ParserFunc | None:
    try:
        module = importlib.import_module(f"worker.state_finances_xlsx.parsers.{module_name}")
    except ModuleNotFoundError:
        return None
    return getattr(module, "parse", None)


def load_directory(directory: str | Path) -> list[IngestStats]:
    """Load every recognised xlsx in ``directory`` into the database."""
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    seen: set[str] = set()
    not_yet_implemented: set[str] = set()
    all_stats: list[IngestStats] = []

    with open_session() as session:
        for path in sorted(directory.iterdir()):
            if path.is_dir():
                continue
            key = path.name.lower()
            if key not in _REGISTRY:
                log.info("Skipping unregistered file: %s", path.name)
                continue
            title, module_name = _REGISTRY[key]
            parser_func = _resolve_parser(module_name)
            if parser_func is None:
                not_yet_implemented.add(path.name)
                continue
            seen.add(key)
            stats = _ingest_file(session, path, title, parser_func)
            all_stats.append(stats)
            session.commit()

    if not_yet_implemented:
        log.info(
            "Skipped %d file(s) without a parser yet: %s",
            len(not_yet_implemented),
            sorted(not_yet_implemented),
        )

    return all_stats


def _ingest_file(
    session: Session,
    path: Path,
    title: str,
    parser_func: ParserFunc,
) -> IngestStats:
    log.info("Ingesting %s", path.name)
    doc = get_or_create_source_document(session, path, title=title)
    parser_run = start_parser_run(session, doc)
    stats = IngestStats(file=path.name)

    try:
        records = list(parser_func(path))
    except Exception:
        log.exception("Parser failed: %s", path.name)
        finish_parser_run(session, parser_run, stats, status=RunStatus.failed)
        return stats

    fiscal_rows = [r for r in records if isinstance(r, FiscalMetricRow)]
    debt_rows = [r for r in records if isinstance(r, DebtInstrumentRow)]

    if fiscal_rows:
        persist_fiscal_metrics(session, doc, parser_run, fiscal_rows, stats)
    if debt_rows:
        persist_debt_instruments(session, doc, parser_run, debt_rows, stats)

    finish_parser_run(session, parser_run, stats)
    log.info(
        "  → file=%s inserted=%d updated=%d instruments=%d positions=%d skipped=%d",
        path.name,
        stats.fiscal_metrics_inserted,
        stats.fiscal_metrics_updated,
        stats.debt_instruments_inserted,
        stats.debt_positions_inserted,
        stats.skipped,
    )
    return stats
