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

## xlsx Baseline-Refresh Procedure

This procedure applies after new RBI State Finances xlsx files are published
(typically when the annual 'State Finances: A Study of Budgets' PDF + xlsx set
is released, usually March–May each year).

### Prerequisites

- Updated xlsx files placed in `Data_website/state_government_dataset/`
- `.env` configured with correct `DATABASE_URL`, `S3_*` vars
- `.venv` activated

### One-shot reload (idempotent)

```bash
cd /home/maveric2/website/public-finance-platform
set -a && source .env && set +a
PYTHONPATH=apps/api:apps/worker:packages/shared-py \
  .venv/bin/python -m worker.state_finances_xlsx.cli load \
  --dir /home/maveric2/website/Data_website/state_government_dataset
```

The loader is **idempotent**: it upserts rows keyed on
`(state_code, metric_code, fiscal_year, basis_tag)` for `fiscal_metrics` and
`(isin, state_code)` for `debt_instruments`. Re-running after updating xlsx
files safely overwrites stale values.

### Verify loaded data

```bash
# Count fiscal_metric rows by metric_group
psql "$DATABASE_URL" -c "
  SELECT metric_group, COUNT(*) FROM fiscal_metrics
  WHERE department_code IS NULL
  GROUP BY metric_group ORDER BY metric_group;"

# AP headline spot-check
psql "$DATABASE_URL" -c "
  SELECT metric_code, fiscal_year, value, basis_tag
  FROM fiscal_metrics
  WHERE state_code = 'AP' AND metric_code IN (
    'total_outstanding_liabilities_pct_gsdp',
    'gross_fiscal_deficit_pct_gsdp',
    'own_tax_revenue_pct_gsdp'
  )
  ORDER BY metric_code, fiscal_year DESC
  LIMIT 15;"
```

### After reload: publish a new release

```bash
# Bump the release version (e.g. xlsx-2026-v2) so downstream caches invalidate
curl -X POST http://localhost:8000/api/v1/admin/releases/publish \
  -H 'Content-Type: application/json' \
  -d '{"release_version": "xlsx-2026-v2", "notes": "RBI State Finances 2026 update"}'
```

### Parser inventory

| File (in `Data_website/state_government_dataset/`) | Parser module |
|---|---|
| `major_fisical_indicators.XLSX` | `major_fiscal_indicators` |
| `revenue_deficit_and_surplus.xlsx` | `revenue_deficit_surplus` |
| `gross_fiscal_deficit_and_surplus.xlsx` | `gross_fiscal_deficit_surplus` |
| `interest_payments.xlsx` | `interest_payments` |
| `tax_revenue.xlsx` | `tax_revenue` |
| `non_tax_revenue.xlsx` | `non_tax_revenue` |
| `total_outstanding_liabilities.xlsx` | `total_outstanding_liabilities` |
| `total_outstanding_liabilities_pct_gsdp.xlsx` | `total_outstanding_liabilities_pct_gsdp` |
| `composition_and_outstanding_liabilities.xlsx` | `composition_outstanding_liabilities` |
| `market_borrowings.xlsx` | `market_borrowings` |
| `loans_from_centre.xlsx` | `loans_from_centre` |
| `outstanding_guarntees_of_state_governments.xlsx` | `guarantees` |
| `maturity_profile_of_outstanding_securities_value.xlsx` | `maturity_profile_value` |
| `maturity_profile_of_outstanding_securities_pct.xlsx` | `maturity_profile_pct` |
| `wages_and_salaries.xlsx` | `wages_salaries` |
| `developmental_expenditure.xlsx` | `developmental_expenditure` |
| `non_developmental_expenditure.xlsx` | `non_developmental_expenditure` |
| `devolution_and_transfers.xlsx` | `devolution_transfers` |
| `interest_payments.xlsx` | `interest_payments` |
| `operations_and_maintenance.xlsx` | `operations_maintenance` |
| `education_expenditure_pct.xlsx` | `education_expenditure_pct` |
| `health_expenditure_pct.xlsx` | `health_expenditure_pct` |
| `social_sector_expenditure.xlsx` | `social_sector_expenditure` |
| `social_sector_expenditure_pct.xlsx` | `social_sector_expenditure_pct` |
| `outstanding_government-securities_asof_may-06-2026.xls` | `outstanding_securities_per_instrument` |
