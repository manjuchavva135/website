# Admin UI Handoff Spec

This document defines frontend integration for the protected admin review panel APIs.

## Auth Contract

All admin endpoints require headers:
- `X-Admin-Email: <authorized-email>`
- `X-Admin-Token: <shared-admin-token>`

Failure behavior:
- `401` when missing admin credentials
- `403` when token/email is invalid

## Base Path

- `/api/v1/admin`

## Endpoints

1. List documents
- `GET /documents?status=<optional>&new_only=<bool>&page=<int>&page_size=<int>`
- Response:
```json
{
  "items": [
    {
      "document_id": 101,
      "source_name": "ap_finance",
      "title": "Budget in Brief 2026-27",
      "parser_version": "2026.04.24",
      "review_status": "pending",
      "checksum_sha256": "...",
      "created_at": "2026-04-24T09:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

2. Document inspection
- `GET /documents/{document_id}`
- Includes extracted rows, page provenance ranges, parser runs, parser warnings/errors, and extracted fact references.
- `parser_runs[]` exposes `status`, `rows_extracted`, `warnings_count`, `started_at`, and `completed_at`.
- `extracted_facts[]` exposes `target_table`, `target_id`, current `review_status`, `confidence_score`, page/row locator fields, quoted source text, and parser notes.

3. Workflow transition (state machine)
- `POST /documents/{document_id}/transition`
```json
{ "to_state": "in_review|approved|rejected|published", "comment": "optional" }
```
- State transitions:
  - `pending -> in_review|approved|rejected`
  - `new -> in_review|approved|rejected`
  - `in_review -> approved|rejected`
  - `rejected -> in_review`
  - `approved -> published`
  - `published` is terminal

4. Approve/reject extracted facts
- `POST /facts/{target_table}/{target_id}/decision`
```json
{ "decision": "approve|reject", "comment": "optional" }
```
- Supported tables: `fiscal_metrics`, `debt_positions`, `debt_events`, `department_spending`, `reconciliation_results`.
- Decisions are append-only in `review_actions`; the latest action for a fact is the review state shown in document detail.

5. Compare conflicting official values
- `GET /conflicts`
- Returns source-to-source comparisons and numeric differences.

6. Annotate reconciliation note
- `POST /reconciliation/{reconciliation_result_id}/annotate`
```json
{ "to_state": "in_review", "comment": "note text" }
```
- `comment` is required; this creates an audit trail event.

7. Re-run parse trigger
- `POST /documents/{document_id}/rerun-parse`
- Returns parser run ID and selected worker task name.
- The API always records a pending parser run and audit event. Worker dispatch is controlled by backend config `DISPATCH_ADMIN_PARSER_JOBS`; local/dev defaults may return a task name without dispatching to Redis.

8. Publish dataset release
- `POST /releases/publish`
```json
{
  "dataset_name": "andhra_public_finance",
  "release_version": "v2026.04.24",
  "release_notes": "what changed",
  "changelog_title": "release title",
  "changelog_details": "release details"
}
```
- Creates:
  - immutable `dataset_releases` row
  - release manifest metadata (`manifest_checksum_sha256`, `manifest_storage_key`)
  - changelog entry
  - release audit action in `review_actions`
- Publish fails with `409` if the release version already exists or if active documents/extracted facts are still pending review.

9. Release history
- `GET /releases/history?dataset_name=<optional>`
- Read-only historical list, newest first.

10. Audit trail
- `GET /audit-trail?entity_table=<optional>&entity_id=<optional>`
- Uses `review_actions` as source of truth.

## Immutable Release Rules

Frontend must treat releases as immutable:
- no edit/delete UI for released versions
- display duplicate version conflict (`409`) inline as validation
- show manifest checksum and key in release details view
- backend blocks ORM-level update/delete of `dataset_releases`; use `/releases/history` as read-only source of truth.

## UX Recommendations

- Show workflow chips: `new`, `in_review`, `approved`, `rejected`, `published`.
- Require confirmation dialogs for approve/reject/publish.
- Render parser warnings and source-row provenance side-by-side.
- For conflicts, render a two-column compare table with delta badges.
- Add an append-only audit timeline panel sourced from `/audit-trail`.

## Error Handling

- `400`: invalid workflow transition or unsupported fact table
- `401/403`: auth failure
- `404`: missing document/fact/reconciliation row
- `409`: duplicate release version
