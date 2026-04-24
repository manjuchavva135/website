from __future__ import annotations

import httpx
from shared_py import S3StorageAdapter
from sqlalchemy import create_engine

from worker.crawler import RawArtifactStorage, SourceDiscoveryCrawler, SourcePersistenceService, SourceRegistry
from worker.celery_app import celery_app
from worker.config import settings
from worker.idempotency import idempotency_store, stable_job_key
from worker.observability import emit_parser_anomaly, report_summary_anomalies


def _source_specs() -> list[dict[str, str]]:
    return [
        {
            "name": entry.source_name,
            "publisher": entry.publisher,
            "url": entry.entrypoint_url,
        }
        for entry in SourceRegistry.default().list_entries()
    ]


@celery_app.task(name="worker.tasks.ingest.fetch_official_sources")
def fetch_official_sources(
    *,
    idempotency_key: str | None = None,
    force: bool = False,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, object]:
    key = idempotency_key or stable_job_key(
        "worker.tasks.ingest.fetch_official_sources",
        {"parser_version": settings.parser_version, "from_date": from_date, "to_date": to_date},
    )
    decision = idempotency_store.acquire(key, force=force)
    if not decision.should_run:
        return {"status": "skipped", "idempotency_key": key, "reason": decision.reason}

    adapter = S3StorageAdapter(
        endpoint_url=settings.s3_endpoint_url,
        region=settings.s3_region,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        use_ssl=settings.s3_use_ssl,
    )

    engine = create_engine(settings.database_url, pool_pre_ping=True)

    crawler = SourceDiscoveryCrawler(
        registry=SourceRegistry.default(),
        repository=SourcePersistenceService(engine=engine),
        storage=RawArtifactStorage(adapter=adapter, bucket_name=settings.s3_bucket),
        http_client=httpx.Client(),
        parser_version=settings.parser_version,
    )
    try:
        result = crawler.crawl_all()
        result["idempotency_key"] = key
        report_summary_anomalies(source_name="official_sources", summary=result, correlation_id=key)
        idempotency_store.mark_complete(key)
        return result
    except Exception as exc:
        emit_parser_anomaly(
            source_name="official_sources",
            anomaly_type="task_exception",
            severity="critical",
            message=str(exc),
            context={"idempotency_key": key},
            correlation_id=key,
        )
        raise
