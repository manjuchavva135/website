# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This is a monorepo containing two distinct projects:

1. **`/agency-agents`** — A reference library of 144+ AI agent personality profiles in Markdown format, organized into 12 divisions (Engineering, Design, Marketing, Sales, etc.). No build step required; use `scripts/install.sh` to install agents into Claude Code or other AI tools.

2. **`/public-finance-platform`** — A production full-stack web app for publishing India's public finance data (Andhra Pradesh). This is the primary application.

## Public Finance Platform

### Tech Stack

- **Frontend:** Next.js 14 (App Router), React 18, TypeScript 5.7, Tailwind CSS, Recharts
- **Backend:** FastAPI, Python 3.11, SQLAlchemy 2, Pydantic v2
- **Workers:** Celery 5.4 with Redis 7
- **Database:** PostgreSQL 16 (production), SQLite (local)
- **Storage:** S3-compatible (MinIO locally)
- **Package managers:** pnpm (JS), pip (Python)

### Key Directories

```
public-finance-platform/
├── apps/web/          # Next.js frontend (App Router)
├── apps/api/          # FastAPI backend
│   └── app/
│       ├── api/       # Route handlers
│       ├── models/    # SQLAlchemy ORM models
│       ├── schemas.py # Pydantic schemas
│       ├── services/  # Business logic
│       └── core/      # Config, middleware
├── apps/worker/       # Celery ingestion workers
├── packages/shared-ts/ # Shared TypeScript contracts
└── packages/shared-py/ # Shared Python utilities (S3 adapter)
```

### Local Development

**With Docker (recommended):**
```bash
cp .env.example .env
pnpm install
pip install -r requirements-dev.txt -r apps/api/requirements.txt -r apps/worker/requirements.txt
pip install -e packages/shared-py
docker compose up --build
```

**Without Docker (three terminals):**
```bash
# API
uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000

# Worker
celery -A worker.celery_app:celery_app --workdir apps/worker worker --loglevel=info

# Web
pnpm dev:web
```

**Local service URLs:** Web `localhost:3000`, API `localhost:8000`, Swagger `localhost:8000/docs`, MinIO console `localhost:9001`

### Build & Test Commands

```bash
pnpm build:web        # Build Next.js
pnpm lint:web         # ESLint
pnpm test:web         # Vitest
pnpm lint:py          # ruff
pnpm format:py        # black
pnpm test:py          # pytest
pnpm lint             # Lint everything
pnpm test             # Test everything
```

**Run a single Python test:**
```bash
cd public-finance-platform && pytest apps/api/tests/test_foo.py::test_bar -v
```

### Database Migrations

```bash
cd public-finance-platform/apps/api
alembic upgrade head                              # Apply migrations
alembic revision --autogenerate -m "description" # Create migration
```

### Architecture Notes

- **Data flow:** Celery workers ingest raw documents from RBI/AP Finance Dept/CAG → store artifacts in S3 → parse and load into PostgreSQL → API serves via FastAPI → Next.js frontend renders
- **Provenance tracking** is maintained at document, page, and row level
- **Trust-first publication model:** documents go through an admin review queue before publication
- **Shared contracts:** TypeScript types in `packages/shared-ts`, Python S3 utilities in `packages/shared-py/shared_py/storage.py`
- **API entry point for Vercel:** `apps/api/vercel_app.py`

### Deployment

- **Frontend + API:** Vercel (see `VERCEL.md`)
- **Workers:** Northflank (see `NORTHFLANK.md`)
- **Operations runbook:** `OPERATIONS.md` (health checks, ingestion procedures, incident response, disaster recovery)

### CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on push to `main`/`master` and all PRs:
- Web job: Node 20, pnpm install, lint, test
- Python job: Python 3.11, ruff, black check, pytest
- Compose job: Docker build smoke test

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
