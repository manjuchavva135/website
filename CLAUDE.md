# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This repository contains a production full-stack web app for publishing India's public finance data (Andhra Pradesh), using a monorepo structure within `/public-finance-platform`.

### Data Sources

The `/Data_website` folder contains raw source documents (51 PDF files, ~101MB) organized by source and fiscal year:
- **Ap_Budget_data/** — Andhra Pradesh Budget documents (2014-15 through 2026-27, multi-volume PDFs per fiscal year)
- **Rbi/** — Reserve Bank of India state securities and debt data
- **Outstanding_securities_state/** — State-level outstanding securities data

These documents are the inputs to the ingestion pipeline. The worker parses these PDFs to extract facts, which are stored with provenance tracking and made available through the API.

## Public Finance Platform

### Tech Stack

- **Frontend:** Next.js 14 (App Router), React 18, TypeScript 5.7, Tailwind CSS, Recharts
- **Backend:** FastAPI, Python 3.12, SQLAlchemy 2, Pydantic v2
- **Workers:** Celery 5.4 with Redis 7
- **Database:** PostgreSQL 16 (local — fully migrated from SQLite)
- **Storage:** S3-compatible (MinIO locally)
- **Package managers:** pnpm (JS), pip (Python)
- **Runtime:** Node 18, Python 3.12, pnpm

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
# API (from platform root)
PYTHONPATH=apps/api .venv/bin/uvicorn app.main:app --app-dir apps/api --host 0.0.0.0 --port 8000

# Worker
celery -A worker.celery_app:celery_app --workdir apps/worker worker --loglevel=info

# Web
pnpm dev:web
```

**Auto-start on boot (Intel NUC — no Docker):**
- All services are registered via `crontab @reboot` to run `start-services.sh` on boot
- Script: `public-finance-platform/start-services.sh`
- Logs: `/tmp/ap-finance-api.log`, `/tmp/ap-finance-web.log`, `/tmp/ap-finance-ngrok.log`, `/tmp/ap-finance-startup.log`
- To check crontab: `crontab -l`

**ngrok external tunnel:**
- Auth token configured in `~/.config/ngrok/ngrok.yml`
- Start: `ngrok http 3000 --log=stdout &`
- Current public URL: `https://oxygen-labored-endorphin.ngrok-free.dev`
- ngrok dashboard: `http://localhost:4040`

**Local service URLs:** Web `localhost:3000`, API `localhost:8000`, Swagger `localhost:8000/docs`

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

**Run a single test:**
```bash
# Python
cd public-finance-platform && pytest apps/api/tests/test_foo.py::test_bar -v

# JavaScript/Vitest
cd public-finance-platform/apps/web && pnpm test -- app/page.test.tsx
```

### Database Migrations

```bash
cd public-finance-platform/apps/api
alembic upgrade head                              # Apply migrations
alembic revision --autogenerate -m "description" # Create migration
```

### Architecture Notes

- **Data flow (baseline mode):** Admin uploads PDFs via `/admin/upload` → S3 storage → Celery `parse_uploaded_document` task → rule-based extractor parses → facts land in PostgreSQL with provenance → admin reviews/approves in `/admin/documents/{id}` → `POST /admin/releases/publish` creates immutable `DatasetRelease` (`baseline-v1`) → API serves approved data → Next.js frontend renders
- **Data flow (auto-fetch mode, post-baseline):** Celery beat fires weekly (Mondays 02:00 UTC) → RBI/AP Finance/CAG crawlers → same parse/review/release pipeline
- **Ingestion mode toggle:** `AUTO_FETCHERS_ENABLED=true` in worker env re-enables the weekly beat schedule. Default is `false` (manual-baseline mode).
- **Pluggable extractor:** `EXTRACTOR_PROVIDER` env var selects `rule_based` (default), `llm` (stub — not yet implemented), or `hybrid`. Set on the worker. Code in `apps/worker/worker/extractors/`. The LLM provider is intentionally undecided — the `ExtractorProvider` interface in `base.py` must support both hosted APIs (Claude) and local models (Ollama/llama.cpp) via a swappable backend without changing the calling code.
- **Provenance tracking** is maintained at document, page, and row level via `ProvenanceLink` records
- **Trust-first publication model:** documents go through an admin review queue (`pending` → `in_review` → `approved`) before being included in a release
- **Shared contracts:** TypeScript types in `packages/shared-ts`, Python S3 utilities in `packages/shared-py/shared_py/storage.py`
- **API entry point for Vercel:** `apps/api/vercel_app.py`
- **S3 adapter:** `shared_py.S3StorageAdapter` — use `upload_bytes(bucket, key, payload, content_type)` and `get_object_bytes(bucket, key)`

### Ingestion Workflow (Manual Baseline)

1. Upload PDFs at `localhost:3000/admin/upload` (source family, source name, optional date/URL/notes)
2. Worker parses each document; document moves to `in_review`
3. Review extracted facts at `/admin/documents/{id}` — approve or reject individual facts
4. Transition document to `approved`
5. `POST /api/v1/admin/releases/publish` with `release_version="baseline-v1"` to lock the baseline
6. Set `AUTO_FETCHERS_ENABLED=true` on the worker and restart beat to begin weekly refreshes

### Remaining / Planned Work

| Item | Status |
|------|--------|
| `apps/worker/worker/extractors/llm.py` — LLM extractor implementation | Stub only — LLM model TBD (Claude API or local Ollama) |
| `apps/api/app/services/admin_review_service.py` — `create_manual_upload()` | Pending |
| Admin review UI — approve/reject individual facts at `/admin/documents/{id}` | Partially implemented |
| `POST /api/v1/admin/releases/publish` to lock `baseline-v1` | Pending |
| Systemd service units for persistent process management | Pending (sudo password required; using crontab @reboot instead) |

---

## Active Redesign (May 2026) — RBI xlsx dataset → AP-first + Peer Comparison

The 2026-05 redesign pivots the site to use the 33 RBI 'State Finances' xlsx tables in `Data_website/state_government_dataset/` plus the per-instrument SDL `.XLS` (5,438 rows). The full plan lives at `~/.claude/plans/reflective-giggling-cray.md`.

**Confirmed product decisions (locked):**
1. Keep the existing pipeline; add an xlsx ingester alongside it.
2. AP-first content; every chart/page has a 'Compare with peers' toggle.
3. Mixed audience — every section page = Story (chart + prose) on top, Data (table + CSV download) below.
4. Dedicated 'Debt Stack' page for the per-instrument SDL list.

### Phase status

| Phase | Scope | Status |
|-------|-------|--------|
| **1. Data layer** | Alembic migration adding `state_code`/`unit_scale` to `fiscal_metrics`, `state_code` to `metric_series`, `issuer_state_code` to `debt_instruments`. New `apps/worker/worker/state_finances_xlsx/` module (loader, persist, CLI, state_codes, 23 statement parsers + per-instrument SDL parser). One-shot baseline load: 9,200 fiscal_metric rows + 4,912 debt_instruments. | ✅ Complete |
| **2. API surface** | Add `state_code` query param (default `'AP'`) to all existing list endpoints + `/debt/summary` + `/debt/maturity-schedule`. New endpoints: `GET /ap/headline`, `GET /ap/debt-composition`, `GET /ap/maturity-profile`, `GET /debt/stack`, `GET /peer-comparison/{metric_code}`, `GET /peer-comparison/_metrics/catalog`. Update `apps/web/lib/api.ts` client. | ✅ Complete |
| **3. Frontend redesign — homepage + Debt section** | New shared `<StoryDataLayout>` + `<PeerCompareToggle>` + `<MultiSeriesLineChart>` components. Rewrite `apps/web/app/page.tsx` (KPI cards from `/ap/headline` + 'how AP compares' strip). Rewire `apps/web/app/debt-overview/page.tsx` to new endpoints + peer toggle. New `apps/web/app/debt-stack/page.tsx` (searchable per-instrument table). Update `app-shell.tsx` nav. | ✅ Complete |
| **4. Frontend — remaining sections** | Rebuild `/deficits`, `/receipts`, `/expenditure` with new data + peer toggle. New `/social-sector` and `/peer-compare` pages. | ✅ Complete (deficits/receipts/expenditure + /peer-compare done; /social-sector pending — no S1 parser yet) |
| **5. Cleanup & deprecation** | S1 parser added (`major_fiscal_indicators.py`, 744 rows). `rbi_ingestion/state_finances_parser.py` marked deprecated. `OPERATIONS.md` updated with xlsx baseline-refresh procedure. `.xlsx_venv/` not found (already clean). Legacy row deletion: 331 `fiscal_metrics` rows with `department_code='AP'` deleted; 9,200 xlsx rows remain. | ✅ Complete |

### Phase 2 — remaining tasks

- [x] 2.1 Service layer (`public_finance_service.py`) accepts `state_code` on `list_debt_outstanding`, `list_debt_events`, `list_fiscal_metrics`, `list_department_spending`.
- [x] 2.2 Existing endpoints in `public_finance.py` expose `state_code` Query param (default `'AP'`); `/debt/summary` + `/debt/maturity-schedule` filter by state too.
- [x] 2.3 New `apps/api/app/api/v1/ap_overview.py` — `/ap/headline`, `/ap/debt-composition`, `/ap/maturity-profile`.
- [x] 2.4 New `apps/api/app/api/v1/debt_stack.py` — `/debt/stack` paginated per-instrument SDL with filters (state/maturity/coupon/search).
- [x] 2.5 New `apps/api/app/api/v1/peers.py` — `/peer-comparison/{metric_code}` (FY snapshot OR multi-year time series across selected states) + `/peer-comparison/_metrics/catalog`.
- [x] 2.6 Register `ap_overview_router`, `debt_stack_router`, `peers_router` in `apps/api/app/main.py`.
- [x] 2.7 Update `apps/web/lib/api.ts` with `api.ap.headline()`, `api.ap.debtComposition(fy)`, `api.ap.maturityProfile()`, `api.debt.stack(filters)`, `api.peers.compare(metricCode, states, fy)`, `api.peers.metricCatalog()`.
- [x] 2.8 Verify with `curl` (each endpoint returns expected shape; peer comparison works for 5 sample states).
- [ ] 2.9 (Stretch) Add pytest coverage in `apps/api/tests/` — `test_ap_overview.py`, `test_debt_stack.py`, `test_peers.py`.

### Critical paths in the new code

- **Data layer**: `apps/api/alembic/versions/20260512_0004_state_dimension.py`; `apps/api/app/models/canonical.py` (`FiscalMetric.state_code`, `FiscalMetric.unit_scale`, `DebtInstrument.issuer_state_code`); `apps/api/app/models/domain.py` (`MetricSeries.state_code`).
- **Loader**: `apps/worker/worker/state_finances_xlsx/{loader,persist,cli,common,records,state_codes}.py` + `parsers/*.py`.
- **CLI to re-load baseline**: `cd public-finance-platform && set -a && source .env && set +a && PYTHONPATH=apps/api:apps/worker:packages/shared-py .venv/bin/python -m worker.state_finances_xlsx.cli load --dir /home/maveric2/website/Data_website/state_government_dataset`
- **API**: `apps/api/app/api/v1/{ap_overview,debt_stack,peers,public_finance}.py`; service in `apps/api/app/services/public_finance_service.py`.

### Caveats & known cleanup

- 1 file (`major_fisical_indicators.XLSX` — Statement 1 ratios) does not yet have a parser. Some appendix tables (Capital Receipts/Expenditure detail) also unparsed. These are additive — none block the redesign.
- Legacy `fiscal_metrics` rows from the pre-migration PDF parser carry `department_code='AP'` as a state-code hack; new xlsx rows have `department_code IS NULL`. All new endpoints filter `department_code IS NULL` to keep the legacy data invisible. Phase 5 deletes those rows.
- Same legacy issue for `debt_instruments`: pre-migration AP SDL rows had `issuer_state_code` NULL until the migration backfilled `'AP'` from `issuer_name`. Re-running the loader is idempotent.

### Deployment

- **Frontend + API:** Vercel (see `VERCEL.md`)
- **Workers:** Northflank (see `NORTHFLANK.md`)
- **Operations runbook:** `OPERATIONS.md` (health checks, ingestion procedures, incident response, disaster recovery)

### CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on push to `main`/`master` and all PRs:
- Web job: Node 20, pnpm install, lint, test
- Python job: Python 3.11, ruff, black check, pytest
- Compose job: Docker build smoke test

### Implemented Features (as of May 2026)

#### Data & Database
- **PostgreSQL 16** running locally — fully migrated from SQLite
- **Baseline ingested:** 9 source documents, 331 fiscal metrics, 996 debt instruments, 996 debt positions, 1327 provenance links
- **Verification:** 76/76 baseline checks passed (`scripts/verify_baseline.py`)

#### API Endpoints (`apps/api/app/api/v1/public_finance.py`)
- `GET /debt/issues` — debt issued
- `GET /debt/pipeline` — scheduled debt pipeline
- `GET /debt/repayments` — debt repayments and service
- `GET /debt/summary` — historical outstanding liabilities + borrowings breakdown (18 years)
- `GET /debt/maturity-schedule` — SDL maturity schedule from Outstanding Securities data
- `GET /fiscal/receipts`, `/fiscal/expenditure`, `/fiscal/deficits`
- `GET /departments/spending`, `/sources`, `/releases`

#### Frontend Pages (`apps/web/app/`)
- **`/debt-overview`** — interactive debt dashboard: 4 KPI cards, historical outstanding area chart (2007-08 to 2025-26), YoY combo bar+line chart, borrowings breakdown chart + table, SDL maturity schedule bar chart
- **`/repayments`** — SDL maturity dashboard: 4 KPI cards, annual maturity bar chart, cumulative area chart, top 10 repayment years, full schedule table
- **`/debt-issuance`**, **`/debt-pipeline`**, **`/receipts`**, **`/expenditure`**, **`/deficits`**, **`/department-spending`**, **`/methodology`**, **`/changelog`**, **`/api-docs`**, **`/health`**, **`/sources`**
- **`/admin/upload`** — PDF upload form
- **`/admin/documents`**, **`/admin/releases`**, **`/admin/review-queue`**, **`/admin/scraper`**, **`/admin/debt-summary`**

#### Chart Components (`apps/web/components/charts/`)
- `area-chart-client.tsx` — area chart with gradient fills and reference lines (Recharts)
- `combo-chart-client.tsx` — dual-axis bar+line combo chart (Recharts)
- `bar-chart-client.tsx`, `time-series-chart.tsx`

#### Frontend API Client (`apps/web/lib/`)
- `api.ts` — main API client: `api.debt.summary()`, `api.debt.maturitySchedule()`, and all other endpoints
- `admin-api.ts` — admin API client: `adminApi.uploadDocument()` etc.
- `api-client.ts`, `api-url.ts`, `csv-export.ts`, `query-params.ts`

#### Extractor Framework (`apps/worker/worker/extractors/`) — IMPLEMENTED
- `base.py` — `ExtractorProvider` ABC (swap-friendly: rule-based, Claude API, or local Ollama)
- `rule_based.py` — wraps existing per-source parsers (RBI, AP Finance, CAG)
- `llm.py` — stub (LLM model TBD)
- `hybrid.py` — LLM + rule-based confidence checks
- `validators.py` — sanity checks: column totals, basis_tag enum, value ranges
- `factory.py` — reads `EXTRACTOR_PROVIDER` env var, returns correct implementation

#### Other Implemented Files
- `apps/api/alembic/versions/20260505_0003_ingestion_mode.py` — adds `ingestion_mode`, `uploaded_by_email` to `source_documents`; makes `source_url` nullable
- `apps/api/app/api/v1/review.py` — `POST /admin/documents/upload` endpoint
- `public-finance-platform/start-services.sh` — boot startup script (crontab @reboot)

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
