# Andhra Pradesh Public Finance Transparency Platform

Production-ready monorepo for a public website and publishable API that ingests official public-finance data from:

- Reserve Bank of India
- Andhra Pradesh Finance Department
- Comptroller and Auditor General of India

The platform publishes debt, receipts, expenditure, deficit, and provenance-aware datasets in JSON and CSV formats.

## Repository Layout

apps/
  web/                   Next.js public portal
  api/                   FastAPI publishable API
  worker/                Celery ingestion workers
packages/
  shared-ts/             shared frontend contracts
  shared-py/             shared backend utilities (S3 adapter)
infra/
  docker/                docker deployment notes
  scripts/               bootstrap scripts

## Core Guarantees

- No unlabeled mixed series across audited actuals, revised estimates, budget estimates, projections, scheduled debt, and issued debt.
- Provenance tracked at document, page, and row level where available.
- Raw source artifacts archived in object storage with checksum and parser version.
- Document review queue for trust-first publication.

## Tech Stack

- Frontend: Next.js App Router, TypeScript, Tailwind
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2
- Migrations: Alembic
- Database: PostgreSQL (or sqlite for local lightweight runs)
- Queue and cache: Redis
- Workers: Celery
- Object Storage: S3-compatible (MinIO in local compose)

## Quick Start

1. Copy environment template

PowerShell:
Copy-Item .env.example .env

Bash:
cp .env.example .env

2. Install JavaScript dependencies

corepack enable
pnpm install

3. Install Python dependencies

python -m pip install -r requirements-dev.txt
python -m pip install -r apps/api/requirements.txt
python -m pip install -r apps/worker/requirements.txt
python -m pip install -e packages/shared-py

## Local Development with Docker

docker compose up --build

Services:

- Web: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- MinIO API: http://localhost:9000
- MinIO console: http://localhost:9001

## Local Development without Docker

1. Start API

uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000

2. Start worker

celery -A worker.celery_app:celery_app --workdir apps/worker worker --loglevel=info

3. Start web app

pnpm dev:web

## Alembic Migrations

From apps/api:

alembic upgrade head

Create a migration:

alembic revision --autogenerate -m "describe change"

## Ingestion Flow

Worker task name: worker.tasks.ingest.fetch_official_sources

What it does:

1. Fetches official source artifacts from configured URLs.
2. Computes sha256 checksum per artifact.
3. Archives raw artifact in S3-compatible storage.
4. Stores source document metadata, parser version, and review status.
5. Stores row-level snippets with row checksum for provenance traces.
6. Logs ingestion run status in ingestion_runs.

## Publishable API Endpoints

- GET /api/v1/metrics
- GET /api/v1/metrics/{slug}/observations
- GET /api/v1/metrics/{slug}/observations.csv
- GET /api/v1/provenance/{observation_id}
- GET /api/v1/admin/review-queue
- PATCH /api/v1/admin/review-queue/{document_id}
- GET /api/v1/changelog

## Public Trust Features

- Source drawer on homepage with per-observation provenance links
- Methodology page describing labeling and ingestion safeguards
- Changelog page for public updates
- Admin review queue page

## Environment Variables

See .env.example for full list.

Key variables:

- DATABASE_URL, POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
- REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- S3_ENDPOINT_URL, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY
- PARSER_VERSION, AUTO_SEED_DATA
- RBI_SOURCE_URL, AP_FINANCE_SOURCE_URL, CAG_SOURCE_URL
- NEXT_PUBLIC_API_BASE_URL

## Tests and Quality

JavaScript:

pnpm lint:web
pnpm test:web

Python:

ruff check apps/api apps/worker packages/shared-py
black --check apps/api apps/worker packages/shared-py
pytest

## CI

GitHub Actions file:

.github/workflows/ci.yml

Pipeline includes web lint and test, python lint and test, and docker compose build smoke test.

## Vercel

The repo includes `vercel.json` for Vercel Services. It deploys the Next.js web app at `/` and FastAPI at `/api`, preserving public API paths such as `/api/v1/health`.

See `VERCEL.md` for dashboard setup, required environment variables, migration requirements, deployment commands, and worker deployment notes.

## Northflank Worker

Deploy the Celery ingestion worker on Northflank with `apps/worker/Dockerfile`.
See `NORTHFLANK.md` for the build context, Dockerfile path, runtime variables,
and backfill/scheduled-job commands.
