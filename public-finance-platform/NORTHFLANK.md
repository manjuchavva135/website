# Northflank Celery Worker

Use Northflank for the Celery worker. Vercel should keep serving only the web
and FastAPI services; ingestion tasks need a long-running worker with Redis.

## Service Setup

Create a Northflank combined service from the GitHub repository:

- Build type: `Dockerfile`
- Build context / working directory: `/public-finance-platform`
- Dockerfile path: `/apps/worker/Dockerfile`
- Public ports: none
- Runtime command: use the image `CMD`
- Instances: start with `1`

The worker command baked into the image is:

```bash
celery -A worker.celery_app:celery_app --workdir apps/worker worker --loglevel=info --concurrency=1
```

Northflank supports Dockerfile builds with a configurable Dockerfile location
and build context. Keep `.dockerignore` in the build context so the deployment
does not upload local virtualenvs, node modules, SQLite files, or test caches.

## Required Runtime Variables

Set these in the Northflank service environment:

```bash
ENV=production
LOG_LEVEL=INFO
PARSER_VERSION=2026.04.24

DATABASE_URL=<same Neon Postgres URL used by Vercel>

REDIS_URL=<redis://...>
CELERY_BROKER_URL=<redis://.../0>
CELERY_RESULT_BACKEND=<redis://.../1>

S3_ENDPOINT_URL=<https://s3-compatible-endpoint>
S3_REGION=<region>
S3_BUCKET=public-finance-data
S3_ACCESS_KEY=<access-key>
S3_SECRET_KEY=<secret-key>
S3_USE_SSL=true

RBI_SOURCE_URL=https://rbi.org.in/
AP_FINANCE_SOURCE_URL=https://finance.ap.gov.in/
CAG_SOURCE_URL=https://cag.gov.in/
```

Use a Redis TCP URL for Celery. A REST-only Redis URL is not enough for Celery
workers. Northflank Redis, Upstash TCP Redis, or another managed Redis endpoint
are acceptable if they expose `redis://` or `rediss://`.

The worker accepts Neon-style `postgresql://...` database URLs and normalizes
them to the installed SQLAlchemy `psycopg` driver at runtime.

## Activating Ingestion Tasks

The Celery worker only executes tasks. Something still has to enqueue them.

For an initial backfill, create a Northflank manual job using the same image and
override the command:

```bash
python -m worker.commands.backfill --source all --from-date 2020-04-01 --to-date 2026-03-31
```

For a safe dry run that only prints deterministic task IDs:

```bash
python -m worker.commands.backfill --source all --from-date 2020-04-01 --to-date 2026-03-31 --dry-run
```

For daily ingestion, create a scheduled Northflank job using the same image:

```bash
python -m worker.commands.backfill --source all
```

The current task names are:

- `worker.tasks.ap_finance_ingest.fetch_ap_finance_data`
- `worker.tasks.rbi_ingest.fetch_rbi_borrowing_data`
- `worker.tasks.ingest.fetch_official_sources`

## Deploy Checklist

1. Run API migrations against the production `DATABASE_URL`.
2. Deploy the Northflank Redis service or connect a managed Redis endpoint.
3. Configure S3-compatible object storage credentials.
4. Deploy the `public-finance-worker` service from `apps/worker/Dockerfile`.
5. Start one worker instance and confirm logs show Celery connected to Redis.
6. Run the dry-run backfill job.
7. Run the real backfill job.
8. Check Vercel API routes after task completion, for example `/api/v1/sources`
   and `/api/v1/debt/issues`.
