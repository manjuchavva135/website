"""CLI: ``python -m worker.state_finances_xlsx.cli load --dir <path>``

Bypasses Celery for the baseline load so a developer can re-seed a fresh
database in one shot. The Celery task in ``worker/tasks/`` will wrap the
same loader for scheduled runs.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from worker.state_finances_xlsx.loader import load_directory


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="state_finances_xlsx")
    sub = parser.add_subparsers(dest="cmd", required=True)

    load = sub.add_parser("load", help="Load every recognised xlsx in a directory")
    load.add_argument("--dir", required=True, type=Path, help="Directory containing the xlsx files")
    load.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if args.cmd == "load":
        all_stats = load_directory(args.dir)
        total_inserted = sum(s.fiscal_metrics_inserted for s in all_stats)
        total_updated = sum(s.fiscal_metrics_updated for s in all_stats)
        total_instruments = sum(s.debt_instruments_inserted for s in all_stats)
        total_positions = sum(s.debt_positions_inserted for s in all_stats)
        total_skipped = sum(s.skipped for s in all_stats)
        print()
        print(
            f"Loaded {len(all_stats)} file(s):"
            f" fiscal_metrics inserted={total_inserted} updated={total_updated}"
            f"; debt_instruments inserted={total_instruments}"
            f"; debt_positions inserted={total_positions}"
            f"; skipped={total_skipped}"
        )
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
