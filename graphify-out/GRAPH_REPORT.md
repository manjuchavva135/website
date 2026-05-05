# Graph Report - public-finance-platform  (2026-05-05)

## Corpus Check
- Corpus is ~45,443 words - fits in a single context window. You may not need a graph.

## Summary
- 781 nodes · 1479 edges · 18 communities detected
- Extraction: 61% EXTRACTED · 39% INFERRED · 0% AMBIGUOUS · INFERRED: 575 edges (avg confidence: 0.76)
- Token cost: 8,500 input · 4,200 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Ingestion & Discovery Tests|Ingestion & Discovery Tests]]
- [[_COMMUNITY_Admin Review Service|Admin Review Service]]
- [[_COMMUNITY_RBI Parser Tests|RBI Parser Tests]]
- [[_COMMUNITY_CAGAP Finance Parsers|CAG/AP Finance Parsers]]
- [[_COMMUNITY_Reparse & Health Ops|Reparse & Health Ops]]
- [[_COMMUNITY_Public API Layer|Public API Layer]]
- [[_COMMUNITY_Admin Review Workflow|Admin Review Workflow]]
- [[_COMMUNITY_Finance Data Service|Finance Data Service]]
- [[_COMMUNITY_AP Finance Fetcher|AP Finance Fetcher]]
- [[_COMMUNITY_Reconciliation Engine|Reconciliation Engine]]
- [[_COMMUNITY_AP Finance Tests|AP Finance Tests]]
- [[_COMMUNITY_Frontend API Client|Frontend API Client]]
- [[_COMMUNITY_Data Table UI|Data Table UI]]
- [[_COMMUNITY_Initial DB Migration|Initial DB Migration]]
- [[_COMMUNITY_Canonical DB Migration|Canonical DB Migration]]
- [[_COMMUNITY_CSV Export|CSV Export]]
- [[_COMMUNITY_Auth Middleware|Auth Middleware]]
- [[_COMMUNITY_Worker Commands|Worker Commands]]

## God Nodes (most connected - your core abstractions)
1. `str()` - 45 edges
2. `Base` - 35 edges
3. `AdminReviewService` - 28 edges
4. `parse_html_document()` - 22 edges
5. `parse_pdf_document()` - 22 edges
6. `AndhraReconciliationService` - 21 edges
7. `parse_cag_annual_accounts()` - 20 edges
8. `PublicFinanceService` - 19 edges
9. `APFinancePersistence` - 19 edges
10. `SourceDocument` - 18 edges

## Surprising Connections (you probably didn't know these)
- `parser_anomalies()` --calls--> `str()`  [INFERRED]
  C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\api\app\api\v1\ops.py → C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\web\lib\query-params.ts
- `_serve_list()` --calls--> `to_csv_response()`  [INFERRED]
  C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\api\app\api\v1\public_finance.py → C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\api\app\api\v1\query_helpers.py
- `get_document_detail()` --calls--> `str()`  [INFERRED]
  C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\api\app\api\v1\review.py → C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\web\lib\query-params.ts
- `transition_document()` --calls--> `str()`  [INFERRED]
  C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\api\app\api\v1\review.py → C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\web\lib\query-params.ts
- `decide_fact()` --calls--> `FactRef`  [INFERRED]
  C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\api\app\api\v1\review.py → C:\Users\wicon_user\Downloads\website\public-finance-platform\apps\api\app\services\admin_review_service.py

## Hyperedges (group relationships)
- **End-to-End Ingestion Pipeline** — readme_celery_worker, readme_redis, readme_s3_storage, readme_postgres [EXTRACTED 0.95]
- **Admin Review and Immutable Release Flow** — admin_review_queue, admin_fact_decision, admin_release_publish, admin_audit_trail [EXTRACTED 0.95]
- **Multi-Source Ingestion Tasks (RBI, AP Finance, CAG)** — northflank_task_rbi, northflank_task_ap_finance, northflank_task_ingest [EXTRACTED 0.95]

## Communities

### Community 0 - "Ingestion & Discovery Tests"
Cohesion: 0.04
Nodes (37): canonicalize_url(), classify_document_family(), detect_anti_bot_page(), detect_anti_bot_signals(), _AnchorParser, DiscoveredLink, extract_page_title(), extract_pdf_links() (+29 more)

### Community 1 - "Admin Review Service"
Cohesion: 0.05
Nodes (54): AdminReviewService, FactRef, ReviewState, BaseModel, ReviewAction, list_changelog(), health(), list_observations() (+46 more)

### Community 2 - "RBI Parser Tests"
Cohesion: 0.05
Nodes (38): score_record_confidence(), compact_whitespace(), parse_date(), APFetchClient, FetchOutcome, extract_pdf_links_from_html(), parse_borrowing_records_from_html(), _pick_value() (+30 more)

### Community 3 - "CAG/AP Finance Parsers"
Cohesion: 0.05
Nodes (54): _dept_code(), _metric_code(), parse_cag_annual_accounts(), _try_add_core_fiscal_metric(), assign_basis_tag(), map_basis_tag(), classify_cag_document_family(), score_debt_event() (+46 more)

### Community 4 - "Reparse & Health Ops"
Cohesion: 0.08
Nodes (52): Base, create_schema(), seed_reference_data(), BudgetHead, DatasetRelease, DatasetReleaseStatus, DebtEvent, DebtEventType (+44 more)

### Community 5 - "Public API Layer"
Cohesion: 0.05
Nodes (33): fmt(), applyFilters(), current(), reset(), configure_logging(), FixedWindowRateLimiter, get_correlation_id(), JsonLogFormatter (+25 more)

### Community 6 - "Admin Review Workflow"
Cohesion: 0.06
Nodes (52): Audit Trail (review_actions table), Source Conflict Comparison Endpoint, Extracted Fact Approve/Reject Decision, Dataset Release Publish API Endpoint, Admin Review Queue (document workflow state machine), Admin UI Handoff Spec, Andhra Pradesh Budget in Brief 2025-26, State Development Loans (SDL) (+44 more)

### Community 7 - "Finance Data Service"
Cohesion: 0.1
Nodes (27): BaseSettings, normalize_database_url(), normalize_hosted_postgres_url(), _parse_string_list(), parse_string_lists(), Settings, WorkerSettings, _cache_key() (+19 more)

### Community 8 - "AP Finance Fetcher"
Cohesion: 0.08
Nodes (23): _ap_finance_source_specs(), fetch_ap_finance_data(), BackfillTaskSpec, build_backfill_plan(), enqueue_backfill(), main(), _CacheEntry, InMemoryTTLCache (+15 more)

### Community 9 - "Reconciliation Engine"
Cohesion: 0.13
Nodes (17): AndhraReconciliationService, _audited_priority(), _is_official_source(), _issuance_priority(), OutputValue, _to_decimal(), _link_provenance(), _seed_source_document() (+9 more)

### Community 10 - "AP Finance Tests"
Cohesion: 0.15
Nodes (12): BasisTag, classify_ap_document_family(), APFinanceSourceSpec, APFinancePersistence, APFinanceIngestionService, APIngestionSummary, test_classifier_maps_known_families(), _fiscal_record() (+4 more)

### Community 11 - "Frontend API Client"
Cohesion: 0.12
Nodes (19): adminFetch(), buildUrl(), apiFetch(), csvDownloadUrl(), apiBaseUrl(), buildApiServiceUrl(), buildApiUrl(), explicitApiBaseUrl() (+11 more)

### Community 12 - "Data Table UI"
Cohesion: 0.33
Nodes (2): formatCell(), isBasisKey()

### Community 13 - "Initial DB Migration"
Cohesion: 0.5
Nodes (1): initial schema  Revision ID: 20260424_0001 Revises:  Create Date: 2026-04-24

### Community 14 - "Canonical DB Migration"
Cohesion: 0.5
Nodes (1): canonical schema  Revision ID: 20260424_0002 Revises: 20260424_0001 Create D

### Community 16 - "CSV Export"
Cohesion: 0.67
Nodes (2): downloadCsv(), rowsToCsv()

### Community 18 - "Auth Middleware"
Cohesion: 1.0
Nodes (2): AdminPrincipal, require_admin()

### Community 39 - "Worker Commands"
Cohesion: 1.0
Nodes (1): Operational worker commands.

## Knowledge Gaps
- **26 isolated node(s):** `initial schema  Revision ID: 20260424_0001 Revises:  Create Date: 2026-04-24`, `canonical schema  Revision ID: 20260424_0002 Revises: 20260424_0001 Create D`, `Simple process-local TTL cache for read-heavy API endpoints.`, `ReviewState`, `CAGDocumentType` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Data Table UI`** (7 nodes): `data-table.tsx`, `formatCell()`, `isAmountKey()`, `isBasisKey()`, `isDateKey()`, `prettyHeader()`, `toggleSort()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Initial DB Migration`** (4 nodes): `downgrade()`, `initial schema  Revision ID: 20260424_0001 Revises:  Create Date: 2026-04-24`, `upgrade()`, `20260424_0001_initial_schema.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Canonical DB Migration`** (4 nodes): `downgrade()`, `canonical schema  Revision ID: 20260424_0002 Revises: 20260424_0001 Create D`, `upgrade()`, `20260424_0002_canonical_schema.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `CSV Export`** (4 nodes): `csv-export.ts`, `downloadCsv()`, `escapeCell()`, `rowsToCsv()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Auth Middleware`** (3 nodes): `auth.py`, `AdminPrincipal`, `require_admin()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Worker Commands`** (2 nodes): `__init__.py`, `Operational worker commands.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `str()` connect `Finance Data Service` to `Ingestion & Discovery Tests`, `Admin Review Service`, `RBI Parser Tests`, `CAG/AP Finance Parsers`, `Public API Layer`, `AP Finance Fetcher`, `Reconciliation Engine`, `AP Finance Tests`, `Frontend API Client`?**
  _High betweenness centrality (0.246) - this node is a cross-community bridge._
- **Why does `infer_fiscal_year()` connect `CAG/AP Finance Parsers` to `Finance Data Service`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `fetch_official_sources()` connect `Ingestion & Discovery Tests` to `AP Finance Fetcher`, `Frontend API Client`, `Finance Data Service`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `str()` (e.g. with `parser_anomalies()` and `get_document_detail()`) actually correct?**
  _`str()` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `Base` (e.g. with `BasisTag` and `SourceDocumentType`) actually correct?**
  _`Base` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `AdminReviewService` (e.g. with `list_review_queue()` and `list_documents()`) actually correct?**
  _`AdminReviewService` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `parse_html_document()` (e.g. with `test_html_parser_extracts_records_and_reconciliation_warning()` and `detect_unit_label()`) actually correct?**
  _`parse_html_document()` has 16 INFERRED edges - model-reasoned connections that need verification._