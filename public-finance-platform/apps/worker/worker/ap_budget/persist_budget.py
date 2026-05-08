"""Optional DB-write path for the budget CLI's --persist flag."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import (
    BasisTag,
    DepartmentSpending,
    ParserRun,
    RunStatus,
)
from worker.ap_budget.budget_parser import ParsedBudgetSpending
from worker.config import settings


_BASIS_MAP = {
    "budgeted": BasisTag.due,
    "revised": BasisTag.due,
    "actual": BasisTag.paid,
}


def persist_budget_rows(records: list[ParsedBudgetSpending]) -> int:
    if not records:
        return 0
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        run = ParserRun(
            source_document_id=None,  # type: ignore[arg-type]
            parser_name="ap_budget_cli",
            parser_version=settings.parser_version,
            status=RunStatus.running,
            rows_extracted=0,
            warnings_count=0,
            started_at=datetime.now(UTC),
        )
        session.add(run)
        session.flush()

        saved = 0
        for rec in records:
            row = DepartmentSpending(
                department_code=rec.department_code,
                department_name=rec.department_name,
                spending_category=rec.spending_category,
                basis_tag=_BASIS_MAP.get(rec.basis_tag, BasisTag.due),
                fiscal_year=rec.fiscal_year,
                period_start=rec.period_start,
                period_end=rec.period_end,
                amount=rec.amount_inr_crore,
                unit=rec.unit,
            )
            session.add(row)
            try:
                session.flush()
                saved += 1
            except Exception:  # noqa: BLE001 — duplicate natural-key collision
                session.rollback()

        run.status = RunStatus.succeeded
        run.rows_extracted = saved
        run.completed_at = datetime.now(UTC)
        session.commit()
        return int(run.id)
