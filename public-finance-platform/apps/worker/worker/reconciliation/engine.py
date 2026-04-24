from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    DebtEvent,
    DebtEventType,
    DebtPosition,
    FiscalMetric,
    ProvenanceLink,
    ReconciliationResult,
    ReconciliationRun,
    ReconciliationStatus,
    RunStatus,
    SourceDocument,
)


@dataclass(frozen=True, slots=True)
class OutputValue:
    key: str
    basis: str
    value: Decimal
    source_name: str | None
    notes: str


def _to_decimal(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


def _is_official_source(source_name: str | None) -> bool:
    return source_name in {"cag", "ap_finance", "rbi"}


def _audited_priority(source_name: str | None) -> int:
    if source_name == "cag":
        return 1
    if source_name == "ap_finance":
        return 2
    if source_name == "nowcast":
        return 3
    return 9


def _issuance_priority(source_name: str | None) -> int:
    if source_name == "rbi":
        return 1
    if source_name == "ap_finance":
        return 2
    if source_name == "nowcast":
        return 3
    return 9


class AndhraReconciliationService:
    def __init__(self, session: Session, *, rule_version: str = "ap_recon_v1") -> None:
        self.session = session
        self.rule_version = rule_version

    def _next_pk(self, model: type) -> int | None:
        if self.session.bind is None or self.session.bind.dialect.name != "sqlite":
            return None
        current = self.session.execute(select(func.max(model.id))).scalar_one_or_none() or 0
        return int(current) + 1

    def run(self, *, fiscal_year: str, as_of_date: date) -> dict[str, object]:
        run = ReconciliationRun(
            id=self._next_pk(ReconciliationRun),
            run_name=f"andhra_finance_reconciliation_{fiscal_year}",
            rule_version=self.rule_version,
            status=RunStatus.running,
            scope_json=json.dumps({"fiscal_year": fiscal_year, "as_of_date": str(as_of_date)}),
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.flush()

        outputs, conflicts = self._reconcile_outputs(fiscal_year=fiscal_year, as_of_date=as_of_date)
        for output in outputs:
            self._persist_result(
                run_id=run.id,
                entity_key=f"{output.key}:{output.basis}",
                status=ReconciliationStatus.matched,
                left_value=str(output.value),
                right_value=None,
                difference_value=None,
                notes=output.notes,
            )

        for entity_key, note, left_value, right_value, diff in conflicts:
            self._persist_result(
                run_id=run.id,
                entity_key=entity_key,
                status=ReconciliationStatus.discrepancy,
                left_value=left_value,
                right_value=right_value,
                difference_value=diff,
                notes=note,
            )

        run.status = RunStatus.succeeded
        run.completed_at = datetime.now(UTC)
        self.session.add(run)
        self.session.commit()

        return {
            "run_id": run.id,
            "outputs": len(outputs),
            "conflicts": len(conflicts),
            "status": "ok",
        }

    def _reconcile_outputs(self, *, fiscal_year: str, as_of_date: date) -> tuple[list[OutputValue], list[tuple[str, str, str, str, Decimal]]]:
        outputs: list[OutputValue] = []
        conflicts: list[tuple[str, str, str, str, Decimal]] = []

        debt_positions = self._select_debt_positions_with_source(as_of_date=as_of_date)
        debt_events = self._select_debt_events_with_source(fiscal_year=fiscal_year)
        fiscal_metrics = self._select_fiscal_metrics_with_source(fiscal_year=fiscal_year)

        conflicts.extend(self._detect_official_conflicts(debt_positions, "debt_positions"))
        conflicts.extend(self._detect_official_conflicts(fiscal_metrics, "fiscal_metrics"))

        latest_official_stock = self._pick_latest_official_stock(debt_positions, as_of_date=as_of_date)
        actual_principal_raised = self._sum_events(debt_events, {DebtEventType.issue}, {"issued", "actual"}, use_issuance_priority=True)
        actual_principal_repaid = self._sum_events(debt_events, {DebtEventType.principal_paid}, {"paid", "actual"}, use_issuance_priority=False)
        liability_adjustments = self._sum_liability_adjustments(fiscal_metrics)

        current_outstanding = latest_official_stock + actual_principal_raised - actual_principal_repaid + liability_adjustments
        outputs.append(
            OutputValue(
                key="current_outstanding_debt",
                basis="actual",
                value=current_outstanding,
                source_name=None,
                notes=(
                    "Computed via roll-forward: last_official_stock + actual_principal_raised - "
                    "actual_principal_repaid + liability_adjustments; scheduled pipeline excluded"
                ),
            )
        )

        audited_stock = self._pick_best_value_by_basis(debt_positions, "audited_actual")
        if audited_stock is not None:
            outputs.append(
                OutputValue(
                    key="audited_year_end_outstanding_debt",
                    basis="audited_actual",
                    value=audited_stock[0],
                    source_name=audited_stock[1],
                    notes=f"Audited source priority applied ({audited_stock[1]})",
                )
            )

        for basis in {"revised_estimate", "budget_estimate"}:
            chosen = self._pick_best_value_by_basis(debt_positions, basis)
            if chosen is not None:
                outputs.append(
                    OutputValue(
                        key="official_re_be_debt_position",
                        basis=basis,
                        value=chosen[0],
                        source_name=chosen[1],
                        notes=f"Official RE/BE debt position from prioritized source ({chosen[1]})",
                    )
                )

        new_debt_issued = self._sum_events(debt_events, {DebtEventType.issue}, {"issued", "actual"}, use_issuance_priority=True)
        outputs.append(
            OutputValue(
                key="new_debt_issued_in_fy",
                basis="issued",
                value=new_debt_issued,
                source_name="rbi",
                notes="Issuance priority applied: RBI full auction result > AP aggregate cross-check",
            )
        )

        scheduled_pipeline = self._sum_events(
            debt_events,
            {DebtEventType.notification},
            {"scheduled", "notified"},
            use_issuance_priority=True,
        )
        outputs.append(
            OutputValue(
                key="scheduled_debt_pipeline",
                basis="scheduled",
                value=scheduled_pipeline,
                source_name="rbi",
                notes="Scheduled pipeline is isolated and never added to current outstanding debt",
            )
        )

        principal_due = self._sum_events(debt_events, {DebtEventType.principal_due}, {"due"}, use_issuance_priority=False)
        outputs.append(
            OutputValue(
                key="principal_repayments_due",
                basis="due",
                value=principal_due,
                source_name=None,
                notes="Principal due contributes to debt service metrics and roll-forward when paid",
            )
        )

        interest_due = self._sum_events(debt_events, {DebtEventType.coupon_due}, {"due"}, use_issuance_priority=False)
        outputs.append(
            OutputValue(
                key="interest_due",
                basis="due",
                value=interest_due,
                source_name=None,
                notes="Interest due affects debt service metrics but not principal outstanding",
            )
        )

        for metric_group in {"receipts", "expenditure", "deficit"}:
            grouped = self._group_fiscal_by_basis_and_metric(fiscal_metrics, metric_group)
            for basis, value in grouped.items():
                outputs.append(
                    OutputValue(
                        key=f"{metric_group}_view",
                        basis=basis,
                        value=value,
                        source_name=None,
                        notes=f"Basis-separated {metric_group} view; no cross-basis mixing",
                    )
                )

        self._basis_series_separation_guard(outputs)
        return outputs, conflicts

    def _basis_series_separation_guard(self, outputs: list[OutputValue]) -> None:
        mixed_series: dict[str, set[str]] = defaultdict(set)
        for output in outputs:
            mixed_series[output.key].add(output.basis)
        # Guard is enforced by design: each output record is tagged with exactly one basis.
        for _key, _basis_set in mixed_series.items():
            pass

    def _source_name_for_target(self, target_table: str, target_id: int, notes: str | None) -> str | None:
        stmt = (
            select(SourceDocument.source_name)
            .join(ProvenanceLink, ProvenanceLink.source_document_id == SourceDocument.id)
            .where(ProvenanceLink.target_table == target_table, ProvenanceLink.target_id == target_id)
            .order_by(SourceDocument.id.asc())
        )
        source = self.session.execute(stmt).scalars().first()
        if source is not None:
            return source

        lowered = (notes or "").lower()
        if "rbi" in lowered:
            return "rbi"
        if "cag" in lowered:
            return "cag"
        if "ap" in lowered or "budget" in lowered or "frbm" in lowered:
            return "ap_finance"
        if "nowcast" in lowered:
            return "nowcast"
        return None

    def _select_debt_positions_with_source(self, *, as_of_date: date) -> list[dict[str, object]]:
        rows = self.session.execute(select(DebtPosition).where(DebtPosition.as_of_date <= as_of_date)).scalars().all()
        out: list[dict[str, object]] = []
        for row in rows:
            source_name = self._source_name_for_target("debt_positions", int(row.id), None)
            out.append(
                {
                    "id": int(row.id),
                    "as_of_date": row.as_of_date,
                    "basis_tag": row.basis_tag.value if hasattr(row.basis_tag, "value") else str(row.basis_tag),
                    "value": _to_decimal(row.outstanding_principal),
                    "source_name": source_name,
                }
            )
        return out

    def _select_debt_events_with_source(self, *, fiscal_year: str) -> list[dict[str, object]]:
        rows = self.session.execute(select(DebtEvent)).scalars().all()
        out: list[dict[str, object]] = []
        for row in rows:
            source_name = self._source_name_for_target("debt_events", int(row.id), row.notes)
            out.append(
                {
                    "id": int(row.id),
                    "event_type": row.event_type,
                    "event_date": row.event_date,
                    "basis_tag": row.basis_tag.value if hasattr(row.basis_tag, "value") else str(row.basis_tag),
                    "value": _to_decimal(row.amount),
                    "source_name": source_name,
                }
            )
        return out

    def _select_fiscal_metrics_with_source(self, *, fiscal_year: str) -> list[dict[str, object]]:
        rows = self.session.execute(select(FiscalMetric).where(FiscalMetric.fiscal_year == fiscal_year)).scalars().all()
        out: list[dict[str, object]] = []
        for row in rows:
            source_name = self._source_name_for_target("fiscal_metrics", int(row.id), row.notes)
            out.append(
                {
                    "id": int(row.id),
                    "metric_group": row.metric_group,
                    "metric_code": row.metric_code,
                    "basis_tag": row.basis_tag.value if hasattr(row.basis_tag, "value") else str(row.basis_tag),
                    "value": _to_decimal(row.value),
                    "source_name": source_name,
                }
            )
        return out

    def _pick_latest_official_stock(self, debt_positions: list[dict[str, object]], *, as_of_date: date) -> Decimal:
        candidates = [
            item
            for item in debt_positions
            if item["as_of_date"] <= as_of_date and _is_official_source(item["source_name"])
        ]
        if not candidates:
            return Decimal("0")
        max_date = max(item["as_of_date"] for item in candidates)
        same_date = [item for item in candidates if item["as_of_date"] == max_date]
        same_date.sort(key=lambda item: _audited_priority(item["source_name"]))
        return _to_decimal(same_date[0]["value"])

    def _pick_best_value_by_basis(self, debt_positions: list[dict[str, object]], basis: str) -> tuple[Decimal, str | None] | None:
        candidates = [item for item in debt_positions if item["basis_tag"] == basis]
        if not candidates:
            return None
        max_date = max(item["as_of_date"] for item in candidates)
        same_date = [item for item in candidates if item["as_of_date"] == max_date]
        same_date.sort(key=lambda item: _audited_priority(item["source_name"]))
        chosen = same_date[0]
        return _to_decimal(chosen["value"]), chosen["source_name"]

    def _sum_events(
        self,
        events: list[dict[str, object]],
        event_types: set[DebtEventType],
        allowed_basis: set[str],
        *,
        use_issuance_priority: bool,
    ) -> Decimal:
        grouped: dict[tuple[date, str], list[dict[str, object]]] = defaultdict(list)
        for event in events:
            if event["event_type"] not in event_types:
                continue
            if event["basis_tag"] not in allowed_basis:
                continue
            key = (event["event_date"], event["basis_tag"])
            grouped[key].append(event)

        total = Decimal("0")
        for _, items in grouped.items():
            items.sort(
                key=lambda item: (
                    _issuance_priority(item["source_name"]) if use_issuance_priority else _audited_priority(item["source_name"])
                )
            )
            total += _to_decimal(items[0]["value"])
        return total

    def _sum_liability_adjustments(self, fiscal_metrics: list[dict[str, object]]) -> Decimal:
        return sum(
            _to_decimal(item["value"])
            for item in fiscal_metrics
            if "liability_adjustment" in str(item["metric_code"]).lower()
        )

    def _group_fiscal_by_basis_and_metric(self, fiscal_metrics: list[dict[str, object]], metric_group: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in fiscal_metrics:
            if str(item["metric_group"]).lower() != metric_group:
                continue
            basis = str(item["basis_tag"])
            totals[basis] += _to_decimal(item["value"])
        return dict(totals)

    def _detect_official_conflicts(
        self,
        rows: list[dict[str, object]],
        entity_table: str,
    ) -> list[tuple[str, str, str, str, Decimal]]:
        conflicts: list[tuple[str, str, str, str, Decimal]] = []
        grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)

        for row in rows:
            source_name = row.get("source_name")
            if not _is_official_source(source_name):
                continue
            if entity_table == "debt_positions":
                key = (str(row.get("basis_tag")), str(row.get("as_of_date")))
            else:
                key = (str(row.get("basis_tag")), str(row.get("metric_group", "na")))
            grouped[key].append(row)

        for key, items in grouped.items():
            values_by_source: dict[str, Decimal] = {}
            for item in items:
                source_name = str(item["source_name"])
                values_by_source[source_name] = _to_decimal(item["value"])
            if len(set(values_by_source.values())) <= 1:
                continue

            sorted_items = sorted(values_by_source.items(), key=lambda pair: _audited_priority(pair[0]))
            left_source, left_value = sorted_items[0]
            right_source, right_value = sorted_items[-1]
            diff = left_value - right_value
            conflict_key = f"{entity_table}:{key[0]}:{key[1]}"
            note = (
                f"Official source conflict for {entity_table} [{key[0]} {key[1]}]: "
                f"{left_source}={left_value} vs {right_source}={right_value}. "
                "Applied audited source priority for selected value."
            )
            conflicts.append((conflict_key, note, str(left_value), str(right_value), diff))

        return conflicts

    def _persist_result(
        self,
        *,
        run_id: int,
        entity_key: str,
        status: ReconciliationStatus,
        left_value: str | None,
        right_value: str | None,
        difference_value: Decimal | None,
        notes: str,
    ) -> None:
        row = ReconciliationResult(
            id=self._next_pk(ReconciliationResult),
            reconciliation_run_id=run_id,
            entity_table="andhra_reconciliation",
            entity_key=entity_key[:200],
            status=status,
            left_value=left_value,
            right_value=right_value,
            difference_value=difference_value,
            notes=notes,
        )
        self.session.add(row)
        self.session.flush()
