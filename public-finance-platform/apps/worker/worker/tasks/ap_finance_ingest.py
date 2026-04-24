from __future__ import annotations

from app.db.session import SessionLocal
from worker.ap_finance_ingestion.fetcher import APFetchClient
from worker.ap_finance_ingestion.models import APFinanceSourceSpec
from worker.ap_finance_ingestion.service import APFinanceIngestionService
from worker.celery_app import celery_app
from worker.config import settings
from worker.idempotency import idempotency_store, stable_job_key
from worker.observability import emit_parser_anomaly, report_summary_anomalies


def _ap_finance_source_specs() -> list[APFinanceSourceSpec]:
    return [
        APFinanceSourceSpec(
            source_family="annual_financial_statement",
            url="https://finance.ap.gov.in/budget.html",
        ),
        APFinanceSourceSpec(
            source_family="demands_for_grants",
            url="https://finance.ap.gov.in/budget.html",
        ),
        APFinanceSourceSpec(
            source_family="detailed_estimates_receipts",
            url="https://finance.ap.gov.in/budget.html",
        ),
        APFinanceSourceSpec(
            source_family="public_account",
            url="https://finance.ap.gov.in/budget.html",
        ),
        APFinanceSourceSpec(
            source_family="budget_in_brief",
            url="https://finance.ap.gov.in/budget.html",
        ),
        APFinanceSourceSpec(
            source_family="frbm_annual",
            url="https://finance.ap.gov.in/frbmreport.html",
        ),
        APFinanceSourceSpec(
            source_family="frbm_quarterly",
            url="https://finance.ap.gov.in/frbmreport.html",
        ),
    ]


@celery_app.task(name="worker.tasks.ap_finance_ingest.fetch_ap_finance_data")
def fetch_ap_finance_data(
    *,
    document_id: int | None = None,
    idempotency_key: str | None = None,
    force: bool = False,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, object]:
    key = idempotency_key or stable_job_key(
        "worker.tasks.ap_finance_ingest.fetch_ap_finance_data",
        {
            "document_id": document_id,
            "parser_version": settings.parser_version,
            "from_date": from_date,
            "to_date": to_date,
        },
    )
    decision = idempotency_store.acquire(key, force=force)
    if not decision.should_run:
        return {"status": "skipped", "idempotency_key": key, "reason": decision.reason}

    service = APFinanceIngestionService(
        fetch_client=APFetchClient(timeout_seconds=30.0, max_retries=3, backoff_seconds=0.5)
    )
    try:
        with SessionLocal() as session:
            summary = service.run(session, _ap_finance_source_specs())
        result = {
            "status": "ok",
            "idempotency_key": key,
            "discovered_documents": summary.discovered_documents,
            "fiscal_metrics_written": summary.fiscal_metrics_written,
            "department_spending_written": summary.department_spending_written,
            "debt_events_written": summary.debt_events_written,
            "debt_positions_written": summary.debt_positions_written,
            "warning_count": summary.warning_count,
            "manual_review_count": summary.manual_review_count,
        }
        report_summary_anomalies(source_name="ap_finance", summary=result, correlation_id=key)
        idempotency_store.mark_complete(key)
        return result
    except Exception as exc:
        emit_parser_anomaly(
            source_name="ap_finance",
            anomaly_type="task_exception",
            severity="critical",
            message=str(exc),
            context={"idempotency_key": key, "document_id": document_id},
            correlation_id=key,
        )
        raise
