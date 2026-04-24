# Vercel Deployment

This repo is configured for Vercel Services:

- `web` serves the Next.js app at `/`.
- `api` serves FastAPI at `/api`.
- External API routes remain `/api/v1/...`.
- The Celery worker is not deployed to Vercel. Run it on a separate worker platform using the same Postgres, Redis, and object-storage settings.

## Dashboard Setup

1. Import the repository into Vercel.
2. Set the project Framework Preset to `Services`.
3. Keep the root directory as the repository root.
4. Configure production environment variables before the first production deploy.

## Required Environment Variables

Set these in Vercel for the API service:

```bash
ENV=production
LOG_LEVEL=INFO
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
S3_ENDPOINT_URL=https://...
S3_REGION=ap-south-1
S3_BUCKET=public-finance-data
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_USE_SSL=true
ADMIN_API_TOKEN=...
ADMIN_ALLOWED_EMAILS=admin@example.gov.in
CORS_ORIGINS=https://your-project.vercel.app
```

The Vercel entrypoint pins `API_BASE_PATH=/v1`, `AUTO_CREATE_SCHEMA=false`, and
`AUTO_SEED_DATA=false` so production cold starts do not mutate the database. If
you need to override these for a temporary preview environment, use
`VERCEL_API_BASE_PATH`, `VERCEL_AUTO_CREATE_SCHEMA`, or `VERCEL_AUTO_SEED_DATA`.

Set these for the web service only if you need to override the default same-origin API routing:

```bash
NEXT_PUBLIC_API_BASE_URL=https://external-api.example.com
```

For same-project Vercel Services, leave `NEXT_PUBLIC_API_BASE_URL` unset. The web app will call `/api/v1/...` on the same deployment URL.

## Database Migration

Vercel cold starts should not create production schema. Run migrations before publishing traffic:

```bash
cd apps/api
alembic upgrade head
```

Use a CI job or one-off administrative runner that has access to `DATABASE_URL`.

## Local Verification

Use Vercel's local builder when you need to verify the service layout:

```bash
vercel dev -L
```

The normal local development commands still work:

```bash
uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000
pnpm dev:web
```

## Deploy

Preview deployment:

```bash
vercel
```

Production deployment:

```bash
vercel --prod
```

CI deployment with prebuilt output:

```bash
vercel pull --yes --environment=production --token=$VERCEL_TOKEN
vercel build --prod --token=$VERCEL_TOKEN
vercel deploy --prebuilt --prod --token=$VERCEL_TOKEN
```

## Post-Deploy Checks

Check these endpoints after each production deploy:

- Web health: `https://your-domain/health`
- API health: `https://your-domain/api/v1/health`
- API readiness: `https://your-domain/api/v1/health/ready`
- Metrics: `https://your-domain/api/v1/ops/metrics`
- OpenAPI: `https://your-domain/api/openapi.json`

## Worker Deployment

Deploy the Celery worker separately with:

```bash
celery -A worker.celery_app:celery_app --workdir apps/worker worker --loglevel=info
```

The worker must use the same `DATABASE_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and S3-compatible object-storage variables as production API.
