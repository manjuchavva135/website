"""CLI: parse RBI auction PDFs + outstanding-securities PDF and reconcile
Andhra Pradesh's outstanding SDL debt. Prints a summary; can optionally
persist results to the database.

Usage:
    python -m worker.commands.ingest_baseline \\
        --rbi-dir /path/to/Data_website/Rbi \\
        --outstanding-dir /path/to/Data_website/Outstanding_securities_state \\
        [--persist]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from worker.rbi_ingestion.ap_reconciliation import (
    ReconciliationSummary,
    reconcile,
)
from worker.rbi_ingestion.models import ParsedBorrowingRecord
from worker.rbi_ingestion.outstanding_parser import (
    OutstandingPosition,
    parse_outstanding_securities,
)
from worker.rbi_ingestion.pdf_parser import parse_borrowing_records_from_pdf


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rbi-dir", required=True, type=Path, help="Directory of RBI auction PDFs")
    parser.add_argument(
        "--outstanding-dir",
        required=True,
        type=Path,
        help="Directory containing the OUTSTANDINGSGSDATA PDF",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Write reconciled DebtPositions + ReconciliationRun to the database",
    )
    return parser.parse_args(argv)


def collect_auction_records(rbi_dir: Path) -> list[ParsedBorrowingRecord]:
    records: list[ParsedBorrowingRecord] = []
    if not rbi_dir.exists():
        return records
    for pdf_path in sorted(rbi_dir.glob("*.pdf")):
        family = (
            "rbi_auction_appendix"
            if "appendix" in pdf_path.name.lower()
            else "rbi_auction"
        )
        records.extend(
            parse_borrowing_records_from_pdf(
                payload=pdf_path.read_bytes(),
                source_url=str(pdf_path),
                source_family=family,
            )
        )
    return records


def collect_outstanding_positions(outstanding_dir: Path) -> list[OutstandingPosition]:
    positions: list[OutstandingPosition] = []
    if not outstanding_dir.exists():
        return positions
    for pdf_path in sorted(outstanding_dir.glob("*.pdf")):
        positions.extend(parse_outstanding_securities(pdf_path))
    return positions


def print_summary(summary: ReconciliationSummary) -> None:
    print("=" * 70)
    print(" Andhra Pradesh — Outstanding SDL Debt Baseline")
    print("=" * 70)
    print(f" Auction events parsed       : {summary.auction_events_total}")
    print(f" Non-AP events dropped       : {summary.auction_events_dropped}")
    print(f" Authoritative positions     : {summary.instruments_authoritative}")
    print(f" Computed-from-events series : {summary.instruments_computed}")
    print("-" * 70)
    print(f" TOTAL OUTSTANDING (INR cr)  : {summary.total_outstanding:,.2f}")
    print("-" * 70)
    if summary.positions:
        print(" By instrument:")
        for pos in summary.positions:
            maturity = pos.maturity_date.isoformat() if pos.maturity_date else "?"
            print(
                f"   - {pos.instrument_code[:48]:<48} "
                f"{pos.outstanding_principal:>14,.2f}  mat={maturity}  src={pos.source}"
            )
    print("=" * 70)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    auction_records = collect_auction_records(args.rbi_dir)
    outstanding_positions = collect_outstanding_positions(args.outstanding_dir)
    summary = reconcile(auction_records, outstanding_positions)
    print_summary(summary)

    if args.persist:
        from worker.rbi_ingestion.persist_baseline import persist_reconciliation

        run_id = persist_reconciliation(summary)
        print(f"Persisted ReconciliationRun id={run_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
