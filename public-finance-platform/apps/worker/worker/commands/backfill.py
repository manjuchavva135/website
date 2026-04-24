from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from worker.celery_app import celery_app
from worker.config import settings
from worker.idempotency import stable_job_key


@dataclass(frozen=True, slots=True)
class BackfillTaskSpec:
    source: str
    task_name: str


TASKS = {
    "discovery": BackfillTaskSpec("discovery", "worker.tasks.ingest.fetch_official_sources"),
    "ap_finance": BackfillTaskSpec("ap_finance", "worker.tasks.ap_finance_ingest.fetch_ap_finance_data"),
    "rbi": BackfillTaskSpec("rbi", "worker.tasks.rbi_ingest.fetch_rbi_borrowing_data"),
}


def build_backfill_plan(
    *,
    source: str,
    from_date: str | None,
    to_date: str | None,
    force: bool,
) -> list[dict[str, Any]]:
    selected = TASKS.values() if source == "all" else [TASKS[source]]
    plan: list[dict[str, Any]] = []
    for spec in selected:
        params = {
            "source": spec.source,
            "parser_version": settings.parser_version,
            "from_date": from_date,
            "to_date": to_date,
        }
        key = stable_job_key(spec.task_name, params)
        plan.append(
            {
                "source": spec.source,
                "task_name": spec.task_name,
                "task_id": key,
                "kwargs": {
                    "idempotency_key": key,
                    "force": force,
                    "from_date": from_date,
                    "to_date": to_date,
                },
            }
        )
    return plan


def enqueue_backfill(plan: list[dict[str, Any]]) -> list[dict[str, str]]:
    queued: list[dict[str, str]] = []
    for item in plan:
        result = celery_app.send_task(
            item["task_name"],
            kwargs=item["kwargs"],
            task_id=item["task_id"],
        )
        queued.append({"source": item["source"], "task_name": item["task_name"], "task_id": result.id})
    return queued


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill historical public-finance source documents")
    parser.add_argument("--source", choices=["all", *TASKS.keys()], default="all")
    parser.add_argument("--from-date", dest="from_date", default=None, help="Inclusive YYYY-MM-DD lower bound")
    parser.add_argument("--to-date", dest="to_date", default=None, help="Inclusive YYYY-MM-DD upper bound")
    parser.add_argument("--force", action="store_true", help="Bypass idempotency lock for controlled replays")
    parser.add_argument("--dry-run", action="store_true", help="Print deterministic task plan without queueing")
    args = parser.parse_args()

    plan = build_backfill_plan(
        source=args.source,
        from_date=args.from_date,
        to_date=args.to_date,
        force=args.force,
    )
    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan}, indent=2, sort_keys=True))
        return 0

    queued = enqueue_backfill(plan)
    print(json.dumps({"queued": queued}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
