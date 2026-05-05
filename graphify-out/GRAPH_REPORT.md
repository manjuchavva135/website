# Graph Report - website  (2026-05-05)

## Corpus Check
- 171 files · ~2,665,019 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1514 nodes · 2802 edges · 176 communities (159 shown, 17 thin omitted)
- Extraction: 65% EXTRACTED · 35% INFERRED · 0% AMBIGUOUS · INFERRED: 986 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2dada793`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

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
- [[_COMMUNITY_Admin State Machine|Admin State Machine]]
- [[_COMMUNITY_CSV Export|CSV Export]]
- [[_COMMUNITY_Alembic Config|Alembic Config]]
- [[_COMMUNITY_Auth Middleware|Auth Middleware]]
- [[_COMMUNITY_Schema Contract Tests|Schema Contract Tests]]
- [[_COMMUNITY_Admin Auth Context|Admin Auth Context]]
- [[_COMMUNITY_Error Boundary|Error Boundary]]
- [[_COMMUNITY_Root Layout|Root Layout]]
- [[_COMMUNITY_Loading State|Loading State]]
- [[_COMMUNITY_Admin Layout|Admin Layout]]
- [[_COMMUNITY_Admin Document Page|Admin Document Page]]
- [[_COMMUNITY_Admin Releases Page|Admin Releases Page]]
- [[_COMMUNITY_Review Queue Page|Review Queue Page]]
- [[_COMMUNITY_Health Route|Health Route]]
- [[_COMMUNITY_Provenance Drawer|Provenance Drawer]]
- [[_COMMUNITY_Source Drawer|Source Drawer]]
- [[_COMMUNITY_Release Workspace|Release Workspace]]
- [[_COMMUNITY_Review Dashboard|Review Dashboard]]
- [[_COMMUNITY_Status Pill UI|Status Pill UI]]
- [[_COMMUNITY_App Shell Nav|App Shell Nav]]
- [[_COMMUNITY_Basis Badge|Basis Badge]]
- [[_COMMUNITY_Last Updated|Last Updated]]
- [[_COMMUNITY_Trust Copy|Trust Copy]]
- [[_COMMUNITY_Worker Config Test|Worker Config Test]]
- [[_COMMUNITY_Worker Commands|Worker Commands]]
- [[_COMMUNITY_Singleton 40|Singleton 40]]
- [[_COMMUNITY_Singleton 42|Singleton 42]]
- [[_COMMUNITY_Singleton 43|Singleton 43]]
- [[_COMMUNITY_Singleton 44|Singleton 44]]
- [[_COMMUNITY_Singleton 45|Singleton 45]]
- [[_COMMUNITY_Singleton 46|Singleton 46]]
- [[_COMMUNITY_Singleton 47|Singleton 47]]
- [[_COMMUNITY_Singleton 50|Singleton 50]]
- [[_COMMUNITY_Singleton 51|Singleton 51]]
- [[_COMMUNITY_Singleton 52|Singleton 52]]
- [[_COMMUNITY_Singleton 53|Singleton 53]]
- [[_COMMUNITY_Singleton 54|Singleton 54]]
- [[_COMMUNITY_Singleton 55|Singleton 55]]
- [[_COMMUNITY_Singleton 57|Singleton 57]]
- [[_COMMUNITY_Singleton 58|Singleton 58]]
- [[_COMMUNITY_Singleton 60|Singleton 60]]
- [[_COMMUNITY_Singleton 62|Singleton 62]]
- [[_COMMUNITY_Singleton 63|Singleton 63]]
- [[_COMMUNITY_Singleton 66|Singleton 66]]
- [[_COMMUNITY_Singleton 69|Singleton 69]]
- [[_COMMUNITY_Singleton 80|Singleton 80]]
- [[_COMMUNITY_Community 99|Community 99]]

## God Nodes (most connected - your core abstractions)
1. `str()` - 46 edges
2. `str()` - 45 edges
3. `Base` - 35 edges
4. `Base` - 35 edges
5. `AdminReviewService` - 28 edges
6. `AdminReviewService` - 28 edges
7. `parse_html_document()` - 22 edges
8. `parse_pdf_document()` - 22 edges
9. `AndhraReconciliationService` - 21 edges
10. `AndhraReconciliationService` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Celery Task: fetch_official_sources` --references--> `CAG Finance Accounts Vol I PDF Fixture`  [INFERRED]
  public-finance-platform/NORTHFLANK.md → public-finance-platform/apps/worker/tests/fixtures/cag/finance_accounts_vol_i.pdf
- `Celery Task: fetch_official_sources` --references--> `CAG Monthly Key Indicators PDF Fixture`  [INFERRED]
  public-finance-platform/NORTHFLANK.md → public-finance-platform/apps/worker/tests/fixtures/cag/monthly_key_indicators.pdf
- `_serve_list()` --calls--> `to_csv_response()`  [INFERRED]
  public-finance-platform/apps/api/app/api/v1/public_finance.py → public-finance-platform/apps/api/app/api/v1/query_helpers.py
- `test_parser_anomaly_reporting_for_manual_review()` --calls--> `report_summary_anomalies()`  [INFERRED]
  public-finance-platform/apps/worker/tests/test_operations.py → public-finance-platform/apps/worker/worker/observability.py
- `test_reconciliation_run_and_results_are_persisted()` --calls--> `AndhraReconciliationService`  [INFERRED]
  public-finance-platform/apps/worker/tests/test_reconciliation_engine.py → public-finance-platform/apps/worker/worker/reconciliation/engine.py

## Hyperedges (group relationships)
- **End-to-End Ingestion Pipeline** — readme_celery_worker, readme_redis, readme_s3_storage, readme_postgres [EXTRACTED 0.95]
- **Admin Review and Immutable Release Flow** — admin_review_queue, admin_fact_decision, admin_release_publish, admin_audit_trail [EXTRACTED 0.95]
- **Multi-Source Ingestion Tasks (RBI, AP Finance, CAG)** — northflank_task_rbi, northflank_task_ap_finance, northflank_task_ingest [EXTRACTED 0.95]

## Communities (176 total, 17 thin omitted)

### Community 0 - "Ingestion & Discovery Tests"
Cohesion: 0.05
Nodes (56): _dept_code(), _metric_code(), parse_cag_annual_accounts(), _try_add_core_fiscal_metric(), assign_basis_tag(), map_basis_tag(), BasisTag, classify_ap_document_family() (+48 more)

### Community 1 - "Admin Review Service"
Cohesion: 0.06
Nodes (39): AdminReviewService, FactRef, ReviewState, _CacheEntry, InMemoryTTLCache, Simple process-local TTL cache for read-heavy API endpoints., _cache_key(), debt_issues() (+31 more)

### Community 2 - "RBI Parser Tests"
Cohesion: 0.05
Nodes (30): canonicalize_url(), classify_document_family(), _AnchorParser, DiscoveredLink, extract_page_title(), extract_pdf_links(), _looks_like_pdf(), CrawlMetrics (+22 more)

### Community 3 - "CAG/AP Finance Parsers"
Cohesion: 0.08
Nodes (56): Base, create_schema(), seed_reference_data(), BudgetHead, DatasetRelease, DatasetReleaseStatus, DebtEvent, DebtEventType (+48 more)

### Community 4 - "Reparse & Health Ops"
Cohesion: 0.05
Nodes (34): score_record_confidence(), compact_whitespace(), parse_date(), extract_pdf_links_from_html(), parse_borrowing_records_from_html(), _pick_value(), _TableParser, RbiIngestionMetrics (+26 more)

### Community 5 - "Public API Layer"
Cohesion: 0.05
Nodes (33): fmt(), applyFilters(), current(), reset(), configure_logging(), FixedWindowRateLimiter, get_correlation_id(), JsonLogFormatter (+25 more)

### Community 6 - "Admin Review Workflow"
Cohesion: 0.06
Nodes (35): map_basis_tag(), classify_ap_document_family(), score_debt_event(), APFetchClient, FetchOutcome, APFinanceSourceSpec, ParsedDebtEventRecord, ParsedDebtPositionRecord (+27 more)

### Community 7 - "Finance Data Service"
Cohesion: 0.06
Nodes (26): _CacheEntry, InMemoryTTLCache, Simple process-local TTL cache for read-heavy API endpoints., HTMLParser, score_record_confidence(), compact_whitespace(), parse_date(), extract_pdf_links_from_html() (+18 more)

### Community 8 - "AP Finance Fetcher"
Cohesion: 0.06
Nodes (52): Audit Trail (review_actions table), Source Conflict Comparison Endpoint, Extracted Fact Approve/Reject Decision, Dataset Release Publish API Endpoint, Admin Review Queue (document workflow state machine), Admin UI Handoff Spec, Andhra Pradesh Budget in Brief 2025-26, State Development Loans (SDL) (+44 more)

### Community 9 - "Reconciliation Engine"
Cohesion: 0.08
Nodes (27): adminFetch(), buildUrl(), apiFetch(), csvDownloadUrl(), apiBaseUrl(), buildApiServiceUrl(), buildApiUrl(), explicitApiBaseUrl() (+19 more)

### Community 10 - "AP Finance Tests"
Cohesion: 0.07
Nodes (29): _ap_finance_source_specs(), fetch_ap_finance_data(), BackfillTaskSpec, build_backfill_plan(), enqueue_backfill(), main(), BaseSettings, normalize_database_url() (+21 more)

### Community 11 - "Frontend API Client"
Cohesion: 0.08
Nodes (17): detect_anti_bot_page(), detect_anti_bot_signals(), FetchClient, FetchOutcome, emit_pipeline_event(), RbiIngestionMetrics, RbiSourceSpec, RbiBorrowingIngestionService (+9 more)

### Community 12 - "Data Table UI"
Cohesion: 0.07
Nodes (27): _dept_code(), _metric_code(), parse_cag_annual_accounts(), _try_add_core_fiscal_metric(), assign_basis_tag(), classify_cag_document_family(), detect_authoritative_or_provisional_notes(), extract_pdf_pages() (+19 more)

### Community 13 - "Initial DB Migration"
Cohesion: 0.11
Nodes (13): formatCell(), isBasisKey(), applyFilters(), csvDownloadUrl(), downloadCsv(), rowsToCsv(), buildFilterUrl(), detectBasis() (+5 more)

### Community 14 - "Canonical DB Migration"
Cohesion: 0.1
Nodes (19): AdminDocumentListResponse, AdminRerunParseResponse, AdminWorkflowStateResponse, DatasetReleaseResponse, ReviewActionResponse, ReviewQueueItem, AdminReviewService, FactRef (+11 more)

### Community 15 - "Admin State Machine"
Cohesion: 0.15
Nodes (12): AndhraReconciliationService, _audited_priority(), _is_official_source(), _issuance_priority(), OutputValue, _to_decimal(), test_reconciliation_run_and_results_are_persisted(), test_settings_accept_vercel_plain_string_list_envs() (+4 more)

### Community 16 - "CSV Export"
Cohesion: 0.14
Nodes (19): Base, DeclarativeBase, BudgetHead, DatasetRelease, DatasetReleaseStatus, DebtEventType, DepartmentSpending, ParserError (+11 more)

### Community 17 - "Alembic Config"
Cohesion: 0.15
Nodes (23): BaseModel, ApiListResponse, DebtEventItem, DebtOutstandingItem, DepartmentSpendingItem, FiscalMetricItem, PaginationMeta, ProvenanceItem (+15 more)

### Community 18 - "Auth Middleware"
Cohesion: 0.17
Nodes (12): ChangelogPage(), getChangelog(), adminFetch(), buildUrl(), apiFetch(), apiBaseUrl(), buildApiServiceUrl(), buildApiUrl() (+4 more)

### Community 19 - "Schema Contract Tests"
Cohesion: 0.12
Nodes (17): list_changelog(), get_provenance(), audit_trail(), get_document_detail(), AdminConflictComparison, AdminDocumentDetail, AdminExtractedFact, AdminFactDecisionRequest (+9 more)

### Community 20 - "Admin Auth Context"
Cohesion: 0.16
Nodes (13): _ap_finance_source_specs(), fetch_ap_finance_data(), fetch_official_sources(), _source_specs(), fetch_rbi_borrowing_data(), _rbi_source_specs(), test_source_specs_contains_seed_urls(), test_stable_job_key_is_deterministic() (+5 more)

### Community 21 - "Error Boundary"
Cohesion: 0.18
Nodes (12): DebtEvent, ParsedBorrowingRecord, _build_event_notes(), _build_instrument_code(), _map_basis_tag(), _map_debt_event_type(), _next_pk(), RbiPersistence (+4 more)

### Community 22 - "Root Layout"
Cohesion: 0.14
Nodes (15): AdminConflictComparison, AdminDocumentDetail, AdminExtractedFact, AdminFactDecisionRequest, AdminParserRunItem, AdminReleasePublishRequest, AdminStateTransitionRequest, ChangelogResponse (+7 more)

### Community 23 - "Loading State"
Cohesion: 0.26
Nodes (14): PublicFinanceService, _cache_key(), debt_issues(), debt_outstanding(), debt_pipeline(), debt_repayments(), department_spending(), fiscal_deficits() (+6 more)

### Community 24 - "Admin Layout"
Cohesion: 0.14
Nodes (4): configure_logging(), FixedWindowRateLimiter, JsonLogFormatter, MetricsRegistry

### Community 25 - "Admin Document Page"
Cohesion: 0.15
Nodes (7): detect_anti_bot_page(), detect_anti_bot_signals(), FakeHttpClient, FakeRepository, FakeStorage, test_checksum_deduplication_skips_duplicate_pdf_uploads(), test_detect_anti_bot_pages()

### Community 26 - "Admin Releases Page"
Cohesion: 0.19
Nodes (7): emit_pipeline_event(), CrawlMetrics, get_crawler_logger(), log_event(), _basename(), _infer_document_type(), SourceDiscoveryCrawler

### Community 27 - "Review Queue Page"
Cohesion: 0.14
Nodes (3): AdminAuthProvider(), useAdminAuth(), StatusPill()

### Community 28 - "Health Route"
Cohesion: 0.29
Nodes (6): _normalize_database_url(), _parse_string_list(), parse_string_lists(), str(), _apply_sort(), ListResult

### Community 29 - "Provenance Drawer"
Cohesion: 0.19
Nodes (10): BackfillTaskSpec, build_backfill_plan(), enqueue_backfill(), main(), test_backfill_plan_uses_deterministic_task_ids(), test_parser_anomaly_reporting_for_manual_review(), test_worker_settings_normalizes_hosted_postgres_url(), normalize_database_url() (+2 more)

### Community 30 - "Source Drawer"
Cohesion: 0.22
Nodes (7): canonicalize_url(), _AnchorParser, DiscoveredLink, extract_page_title(), extract_pdf_links(), _looks_like_pdf(), test_extract_pdf_links_canonicalizes_and_deduplicates()

### Community 31 - "Release Workspace"
Cohesion: 0.18
Nodes (3): _infer_extension(), RawArtifactStorage, S3StorageAdapter

### Community 32 - "Review Dashboard"
Cohesion: 0.2
Nodes (3): _build_id_allocator(), client(), _seed_api_data()

### Community 33 - "Status Pill UI"
Cohesion: 0.32
Nodes (10): seed_reference_data(), SourceDocument, Basis, ChangelogEntry, IngestionRun, MetricGroup, MetricObservation, MetricSeries (+2 more)

### Community 35 - "Basis Badge"
Cohesion: 0.27
Nodes (5): FetchRunRecord, SourceDocumentRecord, SourcePersistenceService, StoredDocument, HttpClient

### Community 36 - "Last Updated"
Cohesion: 0.38
Nodes (8): _build_id_allocator(), _headers(), _seed_admin_data(), test_annotate_rerun_and_release_flow(), test_fact_decision_and_conflict_comparison(), test_invalid_fact_decision_is_rejected(), test_list_documents_and_detail(), test_transition_document_records_review_action()

### Community 37 - "Trust Copy"
Cohesion: 0.24
Nodes (6): fetch_official_sources(), _source_specs(), default(), SourceRegistry, SourceRegistryEntry, test_source_specs_contains_seed_urls()

### Community 38 - "Worker Config Test"
Cohesion: 0.4
Nodes (9): DebtInstrument, DebtPosition, FiscalMetric, _link_provenance(), _seed_source_document(), test_basis_series_separation_receipts_views_are_distinct(), test_reconciliation_persists_conflicts_and_human_readable_notes(), test_reconciliation_run_and_results_are_persisted() (+1 more)

### Community 39 - "Worker Commands"
Cohesion: 0.29
Nodes (6): lifespan(), create_schema(), get_db(), get_engine(), get_session_factory(), SessionLocal()

### Community 43 - "Singleton 43"
Cohesion: 0.4
Nodes (5): MetricObservationResponse, MetricSeriesResponse, list_observations(), list_observations_csv(), list_series()

### Community 44 - "Singleton 44"
Cohesion: 0.4
Nodes (5): list_observations(), list_observations_csv(), list_series(), MetricObservationResponse, MetricSeriesResponse

### Community 46 - "Singleton 46"
Cohesion: 0.4
Nodes (4): worker_health_task(), test_worker_health_without_external_checks(), main(), worker_health()

### Community 50 - "Singleton 50"
Cohesion: 0.47
Nodes (4): map_to_debt_positions_fields(), map_to_department_spending_fields(), map_to_fiscal_metrics_fields(), test_cag_mapper_fields_match_canonical_targets()

### Community 51 - "Singleton 51"
Cohesion: 0.4
Nodes (3): health(), readiness(), HealthResponse

### Community 52 - "Singleton 52"
Cohesion: 0.4
Nodes (3): HealthResponse, health(), readiness()

## Knowledge Gaps
- **35 isolated node(s):** `initial schema  Revision ID: 20260424_0001 Revises:  Create Date: 2026-04-24`, `canonical schema  Revision ID: 20260424_0002 Revises: 20260424_0001 Create D`, `Simple process-local TTL cache for read-heavy API endpoints.`, `ReviewState`, `ProvenanceLocator` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `str()` connect `Health Route` to `RBI Parser Tests`, `Admin Review Workflow`, `Finance Data Service`, `Frontend API Client`, `Data Table UI`, `Initial DB Migration`, `Canonical DB Migration`, `CSV Export`, `Admin Auth Context`, `Root Layout`, `Provenance Drawer`, `Singleton 62`?**
  _High betweenness centrality (0.252) - this node is a cross-community bridge._
- **Why does `str()` connect `Admin Review Service` to `Ingestion & Discovery Tests`, `Basis Badge`, `Reparse & Health Ops`, `Public API Layer`, `Trust Copy`, `Reconciliation Engine`, `AP Finance Tests`, `Admin State Machine`, `Schema Contract Tests`, `Admin Document Page`, `Admin Releases Page`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Why does `ReconciliationRun` connect `CSV Export` to `CAG/AP Finance Parsers`, `Last Updated`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `str()` (e.g. with `parser_anomalies()` and `get_document_detail()`) actually correct?**
  _`str()` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `str()` (e.g. with `parser_anomalies()` and `get_document_detail()`) actually correct?**
  _`str()` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `Base` (e.g. with `BasisTag` and `SourceDocumentType`) actually correct?**
  _`Base` has 33 INFERRED edges - model-reasoned connections that need verification._
- **What connects `initial schema  Revision ID: 20260424_0001 Revises:  Create Date: 2026-04-24`, `canonical schema  Revision ID: 20260424_0002 Revises: 20260424_0001 Create D`, `Simple process-local TTL cache for read-heavy API endpoints.` to the rest of the system?**
  _35 weakly-connected nodes found - possible documentation gaps or missing edges._