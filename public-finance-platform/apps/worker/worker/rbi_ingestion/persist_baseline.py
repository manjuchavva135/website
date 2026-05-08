"""Persist reconciled AP outstanding-debt positions to the database.

Imported lazily by the ``ingest_baseline`` CLI so the parsing path stays
DB-free and unit-testable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from json import dumps

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import (
    BasisTag,
    DebtInstrument,
    DebtPosition,
    ReconciliationRun,
    RunStatus,
)
from worker.config import settings
from worker.rbi_ingestion.ap_reconciliation import ReconciliationSummary


def persist_reconciliation(summary: ReconciliationSummary) -> int:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        run = ReconciliationRun(
            run_name="ap_baseline",
            rule_version=settings.parser_version,
            status=RunStatus.running,
            scope_json=dumps(
                {
                    "scope": "andhra_pradesh_outstanding_sdl",
                    "instruments": len(summary.positions),
                }
            ),
            started_at=datetime.now(UTC),
        )
        session.add(run)
        session.flush()

        for pos in summary.positions:
            instrument = _get_or_create_instrument(session, pos.instrument_code, pos.instrument_name)
            if pos.maturity_date and instrument.maturity_date is None:
                instrument.maturity_date = pos.maturity_date
            if pos.coupon_rate is not None and instrument.coupon_rate is None:
                instrument.coupon_rate = pos.coupon_rate

            existing = session.scalar(
                select(DebtPosition).where(
                    DebtPosition.debt_instrument_id == instrument.id,
                    DebtPosition.as_of_date == (pos.as_of_date or datetime.now(UTC).date()),
                    DebtPosition.basis_tag == BasisTag.actual,
                )
            )
            if existing is None:
                session.add(
                    DebtPosition(
                        debt_instrument_id=instrument.id,
                        as_of_date=pos.as_of_date or datetime.now(UTC).date(),
                        basis_tag=BasisTag.actual,
                        outstanding_principal=pos.outstanding_principal,
                    )
                )
            else:
                existing.outstanding_principal = pos.outstanding_principal

        run.status = RunStatus.succeeded
        run.completed_at = datetime.now(UTC)
        session.commit()
        return int(run.id)


def _get_or_create_instrument(session: Session, code: str, name: str) -> DebtInstrument:
    instrument = session.scalar(
        select(DebtInstrument).where(
            DebtInstrument.source_system == "RBI",
            DebtInstrument.instrument_code == code,
        )
    )
    if instrument is None:
        instrument = DebtInstrument(
            source_system="RBI",
            instrument_code=code,
            instrument_name=name,
            issuer_name="Government of Andhra Pradesh",
            instrument_type="state_development_loan",
            currency="INR",
            is_active=True,
        )
        session.add(instrument)
        session.flush()
    return instrument
