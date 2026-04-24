# Andhra Public-Finance Platform Operations

This runbook covers production hardening, daily operations, incident response, backfills, and disaster recovery for the API, web app, worker, Postgres, Redis, and S3-compatible object storage.

## Production Hardening Architecture

- Web: Next.js serves public pages with CDN-friendly cache headers for static/reference pages and `no-store` for `/admin/*` and `/health`.
- API: FastAPI installs one observability middleware for structured JSON logs, `X-Correlation-ID`, in-process Prometheus-style counters, latency gauges, and fixed-window public API rate limiting.
- Worker: Celery uses late acknowledgements, worker-lost rejection, prefetch `1`, Redis idempotency locks, deterministic task IDs for backfills, and parser anomaly log events.
- Database: Postgres is the system of record for source documents, parser runs, parser errors, provenance, review actions, and immutable dataset releases.
- Object storage: S3-compatible storage is the system of record for raw fetched artifacts and generated release manifests.
- Alerting: scrape `/api/v1/ops/metrics`, alert on `parser_anomalies_total{level="fatal"}`, failed parser runs, sustained 429s, and readiness degradation.

## Health And Readiness

- API liveness: `GET /api/v1/health/live`
- API readiness: `GET /api/v1/health/ready`, checks DB connectivity.
- API metrics: `GET /api/v1/ops/metrics`, Prometheus text format.
- Parser anomaly summary: `GET /api/v1/ops/parser-anomalies`
- Web health: `GET /health`
- Worker health: `python -m worker.health` from `apps/worker`; use `--skip-external` for container startup smoke checks.
- Worker Celery health task: `worker.tasks.health.worker_health`

## Logging And Correlation IDs

- Clients may send `X-Correlation-ID`; otherwise the API generates one.
- API responses echo `X-Correlation-ID`.
- API request logs are JSON with `timestamp`, `level`, `logger`, `message`, `correlation_id`, `method`, `path`, `status_code`, `duration_ms`, and `client_ip`.
- Worker anomaly logs are JSON with `event="parser_anomaly"` and the deterministic idempotency key as the correlation ID for replayable work.

## Metrics And Alerts

Scrape:

```text
/api/v1/ops/metrics
```

Recommended alert rules:

- API readiness degraded for 2 minutes.
- `parser_anomalies_total{level="fatal"} > 0`.
- `parser_runs_total{status="failed"} > 0`.
- 5-minute rate of `http_requests_total{status="429"}` above normal baseline.
- No successful daily ingestion task by expected cutoff.

## Daily Ingestion

1. Confirm readiness: `curl -f https://api.example/api/v1/health/ready`.
2. Queue discovery: `celery -A worker.celery_app:celery_app call worker.tasks.ingest.fetch_official_sources`.
3. Queue AP Finance: `celery -A worker.celery_app:celery_app call worker.tasks.ap_finance_ingest.fetch_ap_finance_data`.
4. Queue RBI: `celery -A worker.celery_app:celery_app call worker.tasks.rbi_ingest.fetch_rbi_borrowing_data`.
5. Review `/api/v1/ops/parser-anomalies` and admin review queue.
6. Approve/reject facts in `/admin/review-queue`.
7. Publish immutable release from `/admin/releases` after pending review work is cleared.

## Failed Job Recovery

- Check Celery worker logs by correlation/idempotency key.
- Check `/api/v1/ops/metrics` for failed parser runs and parser anomalies.
- If the source artifact was fetched and persisted, rerun parse from the admin document detail page.
- If the task died before completion, requeue the same job. Idempotency locks prevent duplicate concurrent execution.
- Use `--force` only after verifying the previous run is not still executing.

## Source-Shape Change Incident Response

1. Treat sudden warning/manual-review spikes as source-shape incidents.
2. Freeze release publication until conflicts and parser warnings are reviewed.
3. Capture the raw source artifact key and parser run ID.
4. Add/adjust parser fixtures matching the changed table/PDF/HTML structure.
5. Run parser tests and a targeted backfill dry run.
6. Reprocess affected date ranges with deterministic backfill keys.
7. Document the parser change in release changelog details.

## Backfills

Dry run:

```bash
cd apps/worker
python -m worker.commands.backfill --source all --from-date 2020-04-01 --to-date 2026-03-31 --dry-run
```

Queue:

```bash
python -m worker.commands.backfill --source ap_finance --from-date 2020-04-01 --to-date 2026-03-31
```

Force replay only after confirming no active run:

```bash
python -m worker.commands.backfill --source rbi --from-date 2024-04-01 --to-date 2025-03-31 --force
```

## Release Rollback

Dataset releases are immutable. Do not edit or delete `dataset_releases`.

Rollback procedure:

1. Publish a new release version that restores the prior approved manifest/fact set.
2. Add a changelog entry explaining the rollback reason and affected release version.
3. Mark superseded UI/API release views by version ordering, not by mutating historical rows.
4. Keep the old manifest and raw artifacts in object storage for auditability.

## Disaster Recovery: Postgres

Backup policy:

- Continuous WAL archiving or managed PITR.
- Daily logical dump for human-readable recovery.
- Before migrations, take a snapshot.

Restore procedure:

1. Provision a clean Postgres instance.
2. Restore the latest base backup and WAL to the chosen timestamp.
3. Validate schema migrations: `alembic current`.
4. Run API readiness: `/api/v1/health/ready`.
5. Run data smoke checks for sources, releases, and admin history.
6. Repoint API and worker `DATABASE_URL`.
7. Requeue missed ingestion windows with `worker.commands.backfill`.

## Disaster Recovery: S3-Compatible Object Storage

Backup policy:

- Enable bucket versioning where supported.
- Replicate raw artifacts and release manifests to a second bucket/account.
- Retain release manifests indefinitely.

Restore procedure:

1. Recreate the bucket with the same name or update `S3_BUCKET`.
2. Restore raw artifact prefixes and `releases/<dataset>/<version>/manifest-*.json`.
3. Verify random object checksums against `source_documents.checksum_sha256`.
4. Run a targeted parser re-run for one document per source.
5. Rebuild affected release manifests only by publishing a new immutable release.

## Cache-Header Policy

- Static Next assets: `public, max-age=31536000, immutable`.
- Static public pages: `public, max-age=300, s-maxage=3600, stale-while-revalidate=86400`.
- Admin and health pages: `no-store`.
- API JSON list responses: short browser max-age and CDN `s-maxage`.
- CSV exports: longer CDN `s-maxage` with stale-while-revalidate.

## Rate Limiting

- Public API endpoints under `/api/v1/*` are rate limited by client IP and path.
- Admin, health, and ops endpoints are excluded.
- Default: `PUBLIC_API_RATE_LIMIT_PER_MINUTE=600`.
- A `429` response includes `Retry-After` and `X-Correlation-ID`.
