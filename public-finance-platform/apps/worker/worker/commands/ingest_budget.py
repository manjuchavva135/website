"""CLI: parse Andhra Pradesh budget volumes from disk into DepartmentSpending.

The input directory is expected to follow the
``Data_website/Ap_Budget_data/<FY>/Volume-*.pdf`` layout where ``<FY>``
matches ``\\d{4}-\\d{2}`` (e.g. ``2024-25``).

Usage:
    python -m worker.commands.ingest_budget \\
        --budget-dir /path/to/Data_website/Ap_Budget_data \\
        [--persist] [--year 2024-25]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from worker.ap_budget.budget_parser import ParsedBudgetSpending, parse_budget_volume


_FY_DIR_RE = re.compile(r"^\d{4}-\d{2}$")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget-dir", required=True, type=Path, help="Root directory of AP budget PDFs")
    parser.add_argument("--year", default=None, help="Process only this fiscal year (e.g. 2024-25)")
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Write extracted DepartmentSpending rows to the database",
    )
    return parser.parse_args(argv)


def collect_records(budget_dir: Path, *, fiscal_year: str | None = None) -> list[ParsedBudgetSpending]:
    records: list[ParsedBudgetSpending] = []
    if not budget_dir.exists():
        return records

    for fy_dir in sorted(p for p in budget_dir.iterdir() if p.is_dir()):
        fy_label = _normalize_fy_label(fy_dir.name)
        if fy_label is None:
            continue
        if fiscal_year and fy_label != fiscal_year:
            continue
        for pdf_path in sorted(fy_dir.glob("*.pdf")):
            records.extend(parse_budget_volume(pdf_path, fy_label))
    return records


def _normalize_fy_label(name: str) -> str | None:
    if _FY_DIR_RE.match(name):
        return name
    # Tolerate suffixes like "2019-20_vote-on_account".
    match = re.match(r"^(\d{4}-\d{2})", name)
    if match:
        return match.group(1)
    return None


def print_summary(records: list[ParsedBudgetSpending]) -> None:
    print("=" * 70)
    print(" Andhra Pradesh — Budget Ingestion Summary")
    print("=" * 70)
    print(f" Records extracted          : {len(records)}")
    by_year: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for rec in records:
        by_year[rec.fiscal_year] = by_year.get(rec.fiscal_year, 0) + 1
        by_category[rec.spending_category] = by_category.get(rec.spending_category, 0) + 1
    print("-" * 70)
    print(" By fiscal year:")
    for fy in sorted(by_year):
        print(f"   {fy:<12}  rows={by_year[fy]}")
    print(" By spending category:")
    for cat in sorted(by_category):
        print(f"   {cat:<24}  rows={by_category[cat]}")
    print("=" * 70)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    records = collect_records(args.budget_dir, fiscal_year=args.year)
    print_summary(records)

    if args.persist:
        from worker.ap_budget.persist_budget import persist_budget_rows

        run_id = persist_budget_rows(records)
        print(f"Persisted budget rows under ParserRun id={run_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
