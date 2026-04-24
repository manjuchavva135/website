from __future__ import annotations

from worker.celery_app import celery_app
from worker.config import settings
from worker.idempotency import idempotency_store, stable_job_key
from worker.rbi_ingestion.fetcher import FetchClient
from worker.rbi_ingestion.models import RbiSourceSpec
from worker.rbi_ingestion.persistence import RbiPersistence
from worker.rbi_ingestion.service import RbiBorrowingIngestionService
from worker.observability import emit_parser_anomaly, report_summary_anomalies


def _rbi_source_specs() -> list[RbiSourceSpec]:
    return [
        RbiSourceSpec(
            source_family="framework",
            url="https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=711",
        ),
        RbiSourceSpec(
            source_family="framework",
            url="https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=3337",
        ),
        RbiSourceSpec(
            source_family="sdl_auction_result",
            url="https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx",
        ),
    ]


@celery_app.task(name="worker.tasks.rbi_ingest.fetch_rbi_borrowing_data")
def fetch_rbi_borrowing_data(
    *,
    document_id: int | None = None,
    idempotency_key: str | None = None,
    force: bool = False,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, object]:
    key = idempotency_key or stable_job_key(
        "worker.tasks.rbi_ingest.fetch_rbi_borrowing_data",
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

    service = RbiBorrowingIngestionService(
        fetch_client=FetchClient(timeout_seconds=30.0, max_retries=3, backoff_seconds=0.5),
        persistence=RbiPersistence(),
        source_specs=_rbi_source_specs(),
    )
    try:
        result = service.run()
        result["idempotency_key"] = key
        report_summary_anomalies(source_name="rbi", summary=result, correlation_id=key)
        idempotency_store.mark_complete(key)
        return result
    except Exception as exc:
        emit_parser_anomaly(
            source_name="rbi",
            anomaly_type="task_exception",
            severity="critical",
            message=str(exc),
            context={"idempotency_key": key, "document_id": document_id},
            correlation_id=key,
        )
        raise
