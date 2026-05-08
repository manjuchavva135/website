"""Recompute AP outstanding-debt reconciliation from current DB state.

Called by the manual-upload task after a debt-relevant document
(rbi_auction or outstanding_securities) is parsed, so the running total
stays current.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from json import dumps

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import (
    BasisTag,
    DebtEvent,
    DebtEventType,
    DebtInstrument,
    DebtPosition,
    ReconciliationRun,
    RunStatus,
)
from worker.config import settings


def recompute_ap_reconciliation() -> int:
    """Rebuild a ReconciliationRun summarizing AP outstanding SDL debt.

    Strategy:
      - Take all DebtPositions on AP instruments as authoritative.
      - For AP instruments without any DebtPosition, sum issuances and
        subtract redemptions from DebtEvents to compute a position.
    """
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        run = ReconciliationRun(
            run_name="ap_outstanding_post_upload",
            rule_version=settings.parser_version,
            status=RunStatus.running,
            started_at=datetime.now(UTC),
        )
        session.add(run)
        session.flush()

        ap_instruments = session.scalars(
            select(DebtInstrument).where(
                DebtInstrument.issuer_name.ilike("%andhra%pradesh%")
            )
        ).all()

        authoritative_count = 0
        computed_count = 0
        total = Decimal("0")

        for inst in ap_instruments:
            position = session.scalar(
                select(DebtPosition)
                .where(DebtPosition.debt_instrument_id == inst.id)
                .order_by(DebtPosition.as_of_date.desc().nullslast())
                .limit(1)
            )
            if position is not None:
                authoritative_count += 1
                total += position.outstanding_principal
                continue

            # Compute from events.
            events = session.scalars(
                select(DebtEvent).where(
                    DebtEvent.debt_instrument_id == inst.id,
                    DebtEvent.basis_tag == BasisTag.actual,
                )
            ).all()
            issued = sum(
                (e.amount for e in events if e.event_type in {DebtEventType.issue, DebtEventType.notification}),
                start=Decimal("0"),
            )
            redeemed = sum(
                (e.amount for e in events if e.event_type == DebtEventType.redemption),
                start=Decimal("0"),
            )
            outstanding = issued - redeemed
            if outstanding <= 0:
                continue
            computed_count += 1
            total += outstanding

        run.scope_json = dumps(
            {
                "scope": "andhra_pradesh_outstanding_sdl",
                "instruments_authoritative": authoritative_count,
                "instruments_computed": computed_count,
                "total_outstanding_inr_crore": str(total),
            }
        )
        run.status = RunStatus.succeeded
        run.completed_at = datetime.now(UTC)
        session.commit()
        return int(run.id)
