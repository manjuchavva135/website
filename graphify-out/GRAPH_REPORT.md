# Graph Report - website  (2026-05-05)

## Corpus Check
- 181 files · ~49,946 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1580 nodes · 3436 edges · 137 communities (120 shown, 17 thin omitted)
- Extraction: 70% EXTRACTED · 30% INFERRED · 0% AMBIGUOUS · INFERRED: 1037 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `640cdac9`
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
- [[_COMMUNITY_Singleton 41|Singleton 41]]
- [[_COMMUNITY_Singleton 42|Singleton 42]]
- [[_COMMUNITY_Singleton 43|Singleton 43]]
- [[_COMMUNITY_Singleton 44|Singleton 44]]
- [[_COMMUNITY_Singleton 45|Singleton 45]]
- [[_COMMUNITY_Singleton 46|Singleton 46]]
- [[_COMMUNITY_Singleton 47|Singleton 47]]
- [[_COMMUNITY_Singleton 48|Singleton 48]]
- [[_COMMUNITY_Singleton 49|Singleton 49]]
- [[_COMMUNITY_Singleton 50|Singleton 50]]
- [[_COMMUNITY_Singleton 51|Singleton 51]]
- [[_COMMUNITY_Singleton 52|Singleton 52]]
- [[_COMMUNITY_Singleton 53|Singleton 53]]
- [[_COMMUNITY_Singleton 54|Singleton 54]]
- [[_COMMUNITY_Singleton 55|Singleton 55]]
- [[_COMMUNITY_Singleton 56|Singleton 56]]
- [[_COMMUNITY_Singleton 57|Singleton 57]]
- [[_COMMUNITY_Singleton 58|Singleton 58]]
- [[_COMMUNITY_Singleton 59|Singleton 59]]
- [[_COMMUNITY_Singleton 60|Singleton 60]]
- [[_COMMUNITY_Singleton 61|Singleton 61]]
- [[_COMMUNITY_Singleton 62|Singleton 62]]
- [[_COMMUNITY_Singleton 63|Singleton 63]]
- [[_COMMUNITY_Singleton 64|Singleton 64]]
- [[_COMMUNITY_Singleton 65|Singleton 65]]
- [[_COMMUNITY_Singleton 66|Singleton 66]]
- [[_COMMUNITY_Singleton 67|Singleton 67]]
- [[_COMMUNITY_Singleton 68|Singleton 68]]
- [[_COMMUNITY_Singleton 69|Singleton 69]]
- [[_COMMUNITY_Singleton 70|Singleton 70]]
- [[_COMMUNITY_Singleton 71|Singleton 71]]

## God Nodes (most connected - your core abstractions)
1. `str()` - 50 edges
2. `str()` - 45 edges
3. `Base` - 37 edges
4. `Base` - 35 edges
5. `AdminReviewService` - 31 edges
6. `AdminReviewService` - 28 edges
7. `LastUpdated()` - 24 edges
8. `BasisBadge()` - 22 edges
9. `parseCommonFilters()` - 22 edges
10. `AndhraReconciliationService` - 22 edges

## Surprising Connections (you probably didn't know these)
- `fetch_official_sources()` --calls--> `S3StorageAdapter`  [INFERRED]
  apps/worker/worker/tasks/ingest.py → packages/shared-py/shared_py/storage.py
- `parse_uploaded_document()` --calls--> `S3StorageAdapter`  [INFERRED]
  apps/worker/worker/tasks/manual_upload.py → packages/shared-py/shared_py/storage.py
- `Celery Task: fetch_official_sources` --references--> `CAG Finance Accounts Vol I PDF Fixture`  [INFERRED]
  public-finance-platform/NORTHFLANK.md → public-finance-platform/apps/worker/tests/fixtures/cag/finance_accounts_vol_i.pdf
- `Celery Task: fetch_official_sources` --references--> `CAG Monthly Key Indicators PDF Fixture`  [INFERRED]
  public-finance-platform/NORTHFLANK.md → public-finance-platform/apps/worker/tests/fixtures/cag/monthly_key_indicators.pdf
- `upload_document()` --calls--> `S3StorageAdapter`  [INFERRED]
  apps/api/app/api/v1/review.py → packages/shared-py/shared_py/storage.py

## Hyperedges (group relationships)
- **End-to-End Ingestion Pipeline** — readme_celery_worker, readme_redis, readme_s3_storage, readme_postgres [EXTRACTED 0.95]
- **Admin Review and Immutable Release Flow** — admin_review_queue, admin_fact_decision, admin_release_publish, admin_audit_trail [EXTRACTED 0.95]
- **Multi-Source Ingestion Tasks (RBI, AP Finance, CAG)** — northflank_task_rbi, northflank_task_ap_finance, northflank_task_ingest [EXTRACTED 0.95]

## Communities (137 total, 17 thin omitted)

### Community 0 - "Ingestion & Discovery Tests"
Cohesion: 0.05
Nodes (82): AdminConflictComparison, AdminDocumentDetail, AdminDocumentListResponse, AdminExtractedFact, AdminFactDecisionRequest, AdminParserRunItem, AdminReleasePublishRequest, AdminRerunParseResponse (+74 more)

### Community 1 - "Admin Review Service"
Cohesion: 0.05
Nodes (53): AdminReviewService, FactRef, ReviewAction, _cache_key(), debt_issues(), debt_outstanding(), debt_pipeline(), debt_repayments() (+45 more)

### Community 2 - "RBI Parser Tests"
Cohesion: 0.05
Nodes (58): _dept_code(), _metric_code(), parse_cag_annual_accounts(), _try_add_core_fiscal_metric(), assign_basis_tag(), _dept_code(), _metric_code(), parse_cag_annual_accounts() (+50 more)

### Community 3 - "CAG/AP Finance Parsers"
Cohesion: 0.06
Nodes (57): map_basis_tag(), classify_ap_document_family(), score_debt_event(), score_debt_position(), score_department_spending(), score_fiscal_metric(), ParsedDebtEventRecord, ParsedDebtPositionRecord (+49 more)

### Community 4 - "Reparse & Health Ops"
Cohesion: 0.06
Nodes (37): _ap_finance_source_specs(), fetch_ap_finance_data(), APFetchClient, FetchOutcome, APFinanceSourceSpec, APFinanceIngestionService, APIngestionSummary, BasisTag (+29 more)

### Community 5 - "Public API Layer"
Cohesion: 0.06
Nodes (34): score_record_confidence(), compact_whitespace(), parse_date(), extract_pdf_links_from_html(), parse_borrowing_records_from_html(), _pick_value(), _TableParser, HTMLParser (+26 more)

### Community 6 - "Admin Review Workflow"
Cohesion: 0.06
Nodes (52): Audit Trail (review_actions table), Source Conflict Comparison Endpoint, Extracted Fact Approve/Reject Decision, Dataset Release Publish API Endpoint, Admin Review Queue (document workflow state machine), Admin UI Handoff Spec, Andhra Pradesh Budget in Brief 2025-26, State Development Loans (SDL) (+44 more)

### Community 7 - "Finance Data Service"
Cohesion: 0.07
Nodes (28): BackfillTaskSpec, build_backfill_plan(), enqueue_backfill(), main(), BackfillTaskSpec, build_backfill_plan(), enqueue_backfill(), main() (+20 more)

### Community 8 - "AP Finance Fetcher"
Cohesion: 0.12
Nodes (12): AndhraReconciliationService, _audited_priority(), _is_official_source(), _issuance_priority(), OutputValue, _to_decimal(), AndhraReconciliationService, _audited_priority() (+4 more)

### Community 9 - "Reconciliation Engine"
Cohesion: 0.1
Nodes (27): adminFetch(), buildUrl(), apiFetch(), csvDownloadUrl(), apiBaseUrl(), buildApiServiceUrl(), buildApiUrl(), explicitApiBaseUrl() (+19 more)

### Community 10 - "AP Finance Tests"
Cohesion: 0.14
Nodes (8): csvDownloadUrl(), detectBasis(), lastUpdatedFromRows(), num(), parseCommonFilters(), BasisBadge(), LastUpdated(), TrustCopy()

### Community 11 - "Frontend API Client"
Cohesion: 0.13
Nodes (32): Base, seed_reference_data(), BudgetHead, DatasetRelease, DebtEvent, DebtInstrument, DebtPosition, DepartmentSpending (+24 more)

### Community 12 - "Data Table UI"
Cohesion: 0.08
Nodes (9): AdminAuthProvider(), useAdminAuth(), decideFact(), rerunParse(), transition(), publish(), saveReconciliationNote(), StatusPill() (+1 more)

### Community 13 - "Initial DB Migration"
Cohesion: 0.11
Nodes (15): ExtractorProvider, Protocol that every extractor implementation must satisfy., fetch_official_sources(), log_event(), FetchRunRecord, SourceDocumentRecord, SourcePersistenceService, StoredDocument (+7 more)

### Community 14 - "Canonical DB Migration"
Cohesion: 0.16
Nodes (28): DatasetReleaseStatus, DebtEventType, ParserErrorLevel, ReconciliationStatus, ReviewActionType, RunStatus, SourceDocumentType, Base (+20 more)

### Community 15 - "Admin State Machine"
Cohesion: 0.1
Nodes (16): ExtractionResult, Unified output from any extractor implementation., get_extractor(), Returns the extractor selected by the EXTRACTOR_PROVIDER env var.     Defaults t, HybridExtractor, Runs LLMExtractor first; if validation fails, falls back to RuleBasedExtractor., LLMExtractor, Stub for LLM-based PDF extraction.      TODO: Implement once the model is chosen (+8 more)

### Community 16 - "CSV Export"
Cohesion: 0.11
Nodes (11): classify_document_family(), classify_document_family(), FakeStorage, test_classification_rules_cover_core_families(), FakeHttpClient, FakeRepository, FakeStorage, test_checksum_deduplication_skips_duplicate_pdf_uploads() (+3 more)

### Community 17 - "Alembic Config"
Cohesion: 0.15
Nodes (11): canonicalize_url(), log_event(), FetchRunRecord, SourceDocumentRecord, SourcePersistenceService, StoredDocument, _basename(), HttpClient (+3 more)

### Community 18 - "Auth Middleware"
Cohesion: 0.14
Nodes (20): get_correlation_id(), _extract_links_from_html(), test_admin_routes_require_auth(), test_all_requested_endpoints_return_paginated_payloads(), test_ambiguous_as_of_and_range_returns_400(), test_ambiguous_basis_input_returns_400(), test_csv_export_supported_for_all_requested_endpoints(), test_filter_sort_and_pagination() (+12 more)

### Community 19 - "Schema Contract Tests"
Cohesion: 0.21
Nodes (20): ParserError, SourcePage, _build_id_allocator(), _headers(), _seed_admin_data(), test_annotate_rerun_and_release_flow(), test_fact_decision_and_conflict_comparison(), test_invalid_fact_decision_is_rejected() (+12 more)

### Community 20 - "Admin Auth Context"
Cohesion: 0.18
Nodes (9): RbiSourceSpec, _looks_like_pdf(), RbiBorrowingIngestionService, FailingPdfFetcher, StubFetcher, StubPersistence, test_service_creates_manual_review_when_anti_bot_detected(), test_service_skips_broken_or_non_pdf_links_without_failing_task() (+1 more)

### Community 21 - "Error Boundary"
Cohesion: 0.14
Nodes (12): canonicalize_url(), _AnchorParser, DiscoveredLink, extract_page_title(), extract_pdf_links(), _looks_like_pdf(), _AnchorParser, DiscoveredLink (+4 more)

### Community 22 - "Root Layout"
Cohesion: 0.18
Nodes (15): lifespan(), root(), create_schema(), create_schema(), seed_reference_data(), lifespan(), SourceDocument, Basis (+7 more)

### Community 23 - "Loading State"
Cohesion: 0.14
Nodes (13): downloadCsv(), rowsToCsv(), formatCell(), isAmountKey(), isBasisKey(), isDateKey(), prettyHeader(), toggleSort() (+5 more)

### Community 24 - "Admin Layout"
Cohesion: 0.19
Nodes (12): _build_event_notes(), _map_basis_tag(), _map_debt_event_type(), _next_pk(), _resolve_amount(), _build_event_notes(), _build_instrument_code(), _map_basis_tag() (+4 more)

### Community 25 - "Admin Document Page"
Cohesion: 0.17
Nodes (9): ParsedBorrowingRecord, RbiPersistence, ParsedBorrowingRecord, _record(), test_idempotent_upsert_for_instruments_and_events(), test_manual_review_task_is_persisted(), _record(), test_idempotent_upsert_for_instruments_and_events() (+1 more)

### Community 27 - "Review Queue Page"
Cohesion: 0.21
Nodes (8): FetchOutcome, RbiIngestionMetrics, RbiSourceSpec, RbiBorrowingIngestionService, StubFetcher, StubPersistence, test_service_creates_manual_review_when_anti_bot_detected(), test_service_stores_wma_context_when_no_structured_rows()

### Community 28 - "Health Route"
Cohesion: 0.16
Nodes (10): normalize_database_url(), normalize_hosted_postgres_url(), WorkerSettings, test_worker_settings_normalizes_hosted_postgres_url(), test_worker_has_broker_url(), test_worker_requires_non_empty_s3_bucket(), normalize_database_url(), normalize_hosted_postgres_url() (+2 more)

### Community 29 - "Provenance Drawer"
Cohesion: 0.19
Nodes (12): reset(), test_correlation_id_is_echoed(), test_health_endpoint(), test_parser_anomaly_summary_shape(), test_public_api_rate_limiting(), test_readiness_and_prometheus_metrics(), client(), test_correlation_id_is_echoed() (+4 more)

### Community 30 - "Source Drawer"
Cohesion: 0.18
Nodes (4): _infer_extension(), RawArtifactStorage, _infer_extension(), RawArtifactStorage

### Community 32 - "Review Dashboard"
Cohesion: 0.22
Nodes (6): FetchClient, FetchOutcome, AntiBotTransport, FlakyTransport, test_fetcher_flags_anti_bot_signals(), test_fetcher_retries_on_transient_failures()

### Community 33 - "Status Pill UI"
Cohesion: 0.21
Nodes (6): configure_logging(), FixedWindowRateLimiter, get_correlation_id(), install_observability(), is_public_api_path(), JsonLogFormatter

### Community 34 - "App Shell Nav"
Cohesion: 0.21
Nodes (8): fmt(), fmt(), configure_logging(), JsonLogFormatter, configure_logging(), emit_parser_anomaly(), JsonLogFormatter, report_summary_anomalies()

### Community 35 - "Basis Badge"
Cohesion: 0.4
Nodes (12): DebtEvent, ProvenanceLink, _get_or_create_instrument(), _get_or_create_page(), parse_uploaded_document(), _persist_result(), Persist RBI ParsedBorrowingRecord as DebtInstrument + DebtEvent pairs., _save_borrowing_records() (+4 more)

### Community 36 - "Last Updated"
Cohesion: 0.27
Nodes (6): FetchClient, client(), AntiBotTransport, FlakyTransport, test_fetcher_flags_anti_bot_signals(), test_fetcher_retries_on_transient_failures()

### Community 37 - "Trust Copy"
Cohesion: 0.28
Nodes (11): AdminWorkflowStateResponse, audit_trail(), annotate_reconciliation(), audit_trail(), compare_conflicts(), list_documents(), list_review_queue(), publish_release() (+3 more)

### Community 38 - "Worker Config Test"
Cohesion: 0.41
Nodes (10): DebtInstrument, DebtPosition, FiscalMetric, _seed_api_data(), _link_provenance(), _seed_source_document(), test_basis_series_separation_receipts_views_are_distinct(), test_reconciliation_persists_conflicts_and_human_readable_notes() (+2 more)

### Community 39 - "Worker Commands"
Cohesion: 0.23
Nodes (9): test_metrics_csv_download(), test_metrics_observations_do_not_mix_unlabeled_basis(), test_metrics_series_available(), test_review_queue_endpoint_exists(), client(), test_metrics_csv_download(), test_metrics_observations_do_not_mix_unlabeled_basis(), test_metrics_series_available() (+1 more)

### Community 40 - "Singleton 40"
Cohesion: 0.21
Nodes (4): CrawlMetrics, get_crawler_logger(), CrawlMetrics, get_crawler_logger()

### Community 41 - "Singleton 41"
Cohesion: 0.18
Nodes (4): InMemoryTTLCache, Simple process-local TTL cache for read-heavy API endpoints., FixedWindowRateLimiter, test_cache_hit_header_on_repeat_read()

### Community 42 - "Singleton 42"
Cohesion: 0.24
Nodes (5): MetricsRegistry, parser_anomalies(), prometheus_metrics(), parser_anomalies(), prometheus_metrics()

### Community 43 - "Singleton 43"
Cohesion: 0.29
Nodes (9): BaseSettings, _parse_string_list(), parse_string_lists(), Settings, _normalize_database_url(), _parse_string_list(), parse_string_lists(), require_non_empty_s3_config() (+1 more)

### Community 44 - "Singleton 44"
Cohesion: 0.22
Nodes (4): _CacheEntry, _CacheEntry, InMemoryTTLCache, Simple process-local TTL cache for read-heavy API endpoints.

### Community 45 - "Singleton 45"
Cohesion: 0.4
Nodes (8): get_db(), get_engine(), get_session_factory(), SessionLocal(), get_db(), get_engine(), get_session_factory(), SessionLocal()

### Community 46 - "Singleton 46"
Cohesion: 0.44
Nodes (3): str(), _apply_sort(), ListResult

### Community 48 - "Singleton 48"
Cohesion: 0.33
Nodes (7): emit_parser_anomaly(), report_summary_anomalies(), fetch_rbi_borrowing_data(), _rbi_source_specs(), fetch_rbi_borrowing_data(), _rbi_source_specs(), test_parser_anomaly_reporting_for_manual_review()

### Community 49 - "Singleton 49"
Cohesion: 0.33
Nodes (7): applyFilters(), current(), reset(), applyFilters(), current(), buildFilterUrl(), buildFilterUrl()

### Community 50 - "Singleton 50"
Cohesion: 0.28
Nodes (5): _source_specs(), fetch_official_sources(), _source_specs(), test_source_specs_contains_seed_urls(), test_source_specs_contains_seed_urls()

### Community 51 - "Singleton 51"
Cohesion: 0.33
Nodes (5): default(), SourceRegistry, SourceRegistryEntry, default(), SourceRegistryEntry

### Community 52 - "Singleton 52"
Cohesion: 0.32
Nodes (4): initial schema  Revision ID: 20260424_0001 Revises:  Create Date: 2026-04-24, downgrade(), initial schema  Revision ID: 20260424_0001 Revises:  Create Date: 2026-04-24, upgrade()

### Community 53 - "Singleton 53"
Cohesion: 0.32
Nodes (4): canonical schema  Revision ID: 20260424_0002 Revises: 20260424_0001 Create D, downgrade(), canonical schema  Revision ID: 20260424_0002 Revises: 20260424_0001 Create D, upgrade()

### Community 54 - "Singleton 54"
Cohesion: 0.33
Nodes (3): emit_pipeline_event(), emit_pipeline_event(), RbiIngestionMetrics

### Community 55 - "Singleton 55"
Cohesion: 0.43
Nodes (5): detect_anti_bot_page(), detect_anti_bot_signals(), detect_anti_bot_page(), detect_anti_bot_signals(), test_detect_anti_bot_pages()

### Community 58 - "Singleton 58"
Cohesion: 0.53
Nodes (4): AdminPrincipal, require_admin(), AdminPrincipal, require_admin()

### Community 61 - "Singleton 61"
Cohesion: 0.4
Nodes (4): ReviewState, FactRef, ReviewState, decide_fact()

## Knowledge Gaps
- **37 isolated node(s):** `ingestion mode  Revision ID: 20260505_0003 Revises: 20260424_0002 Create Date: 2`, `Simple process-local TTL cache for read-heavy API endpoints.`, `Unified output from any extractor implementation.`, `Protocol that every extractor implementation must satisfy.`, `Returns the extractor selected by the EXTRACTOR_PROVIDER env var.     Defaults t` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `str()` connect `Singleton 46` to `Ingestion & Discovery Tests`, `RBI Parser Tests`, `CAG/AP Finance Parsers`, `Reparse & Health Ops`, `Public API Layer`, `AP Finance Fetcher`, `AP Finance Tests`, `Alembic Config`, `Admin Auth Context`, `Admin Releases Page`, `Health Route`, `Review Dashboard`, `App Shell Nav`, `Basis Badge`, `Trust Copy`, `Singleton 42`, `Singleton 43`, `Singleton 44`, `Singleton 48`, `Singleton 50`, `Singleton 55`, `Singleton 61`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Why does `str()` connect `Admin Review Service` to `Ingestion & Discovery Tests`, `RBI Parser Tests`, `CAG/AP Finance Parsers`, `Reparse & Health Ops`, `Public API Layer`, `Last Updated`, `AP Finance Fetcher`, `AP Finance Tests`, `Singleton 43`, `Singleton 42`, `Initial DB Migration`, `Singleton 48`, `Singleton 55`, `Admin Document Page`, `Health Route`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Why does `parseCommonFilters()` connect `AP Finance Tests` to `Singleton 46`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `str()` (e.g. with `parser_anomalies()` and `get_document_detail()`) actually correct?**
  _`str()` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `str()` (e.g. with `parser_anomalies()` and `get_document_detail()`) actually correct?**
  _`str()` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `Base` (e.g. with `BasisTag` and `SourceDocumentType`) actually correct?**
  _`Base` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ingestion mode  Revision ID: 20260505_0003 Revises: 20260424_0002 Create Date: 2`, `Simple process-local TTL cache for read-heavy API endpoints.`, `Unified output from any extractor implementation.` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._