import { buildApiUrl } from "./api-url";

export type AdminCredentials = {
  email: string;
  token: string;
};

export type ReviewQueueItem = {
  document_id: number;
  source_name: string;
  title: string;
  parser_version: string | null;
  review_status: string;
  checksum_sha256: string;
  created_at: string;
};

export type AdminDocumentListResponse = {
  items: ReviewQueueItem[];
  total: number;
  page: number;
  page_size: number;
};

export type ParserRunItem = {
  id: number;
  parser_name: string;
  parser_version: string;
  status: string;
  rows_extracted: number;
  warnings_count: number;
  started_at: string;
  completed_at: string | null;
};

export type ParserErrorItem = {
  id: number;
  error_level: string;
  error_code: string | null;
  message: string;
  row_number: number | null;
  column_name: string | null;
  raw_value: string | null;
  created_at: string;
};

export type ExtractedFact = {
  target_table: string;
  target_id: number;
  review_status: string;
  confidence_score: string | number | null;
  source_page_id: number | null;
  page_number: number | null;
  row_number: number | null;
  row_label: string | null;
  column_name: string | null;
  cell_ref: string | null;
  quoted_text: string | null;
  notes: string | null;
};

export type AdminDocumentDetail = {
  document_id: number;
  source_name: string;
  title: string;
  review_status: string;
  parser_version: string | null;
  rows: Array<{
    id: number;
    page_number: number | null;
    row_number: number | null;
    row_label: string | null;
    raw_text: string;
    checksum_sha256: string;
  }>;
  pages: Array<{
    id: number;
    page_number: number;
    page_label: string | null;
    row_start: number | null;
    row_end: number | null;
  }>;
  parser_runs: ParserRunItem[];
  parser_errors: ParserErrorItem[];
  extracted_facts: ExtractedFact[];
};

export type ConflictComparison = {
  entity: string;
  basis_tag: string;
  left_source: string;
  left_value: string;
  right_source: string;
  right_value: string;
  difference: string;
  metric_code?: string | null;
  period_end?: string | null;
  as_of_date?: string | null;
};

export type ReleaseRecord = {
  id: number;
  dataset_name: string;
  release_version: string;
  status: string;
  release_notes: string | null;
  manifest_checksum_sha256: string | null;
  manifest_storage_key: string | null;
  published_at: string | null;
  created_at: string;
};

export type ReviewAction = {
  id: number;
  entity_table: string;
  entity_id: number;
  action_type: string;
  review_status: string;
  actor_email: string | null;
  comments: string | null;
  acted_at: string;
  source_document_id: number | null;
};

export type RerunParseResponse = {
  parser_run_id: number;
  task_name: string | null;
  status: string;
};

export type ManualUploadResponse = {
  document_id: number;
  checksum_sha256: string;
  storage_key: string;
  review_status: string;
  duplicate: boolean;
};

type FetchParams = Record<string, string | number | boolean | null | undefined>;

function buildUrl(path: string, params: FetchParams = {}): string {
  return buildApiUrl(`/api/v1/admin${path}`, params);
}

async function adminFetch<T>(
  credentials: AdminCredentials,
  path: string,
  init: RequestInit = {},
  params: FetchParams = {},
): Promise<T> {
  const response = await fetch(buildUrl(path, params), {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Email": credentials.email,
      "X-Admin-Token": credentials.token,
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export const adminApi = {
  documents: (credentials: AdminCredentials, params: FetchParams = {}) =>
    adminFetch<AdminDocumentListResponse>(credentials, "/documents", {}, params),

  document: (credentials: AdminCredentials, documentId: number) =>
    adminFetch<AdminDocumentDetail>(credentials, `/documents/${documentId}`),

  transitionDocument: (
    credentials: AdminCredentials,
    documentId: number,
    toState: string,
    comment?: string,
  ) =>
    adminFetch<{ entity_table: string; entity_id: number; state: string }>(
      credentials,
      `/documents/${documentId}/transition`,
      {
        method: "POST",
        body: JSON.stringify({ to_state: toState, comment }),
      },
    ),

  decideFact: (
    credentials: AdminCredentials,
    targetTable: string,
    targetId: number,
    decision: "approve" | "reject",
    comment?: string,
  ) =>
    adminFetch<{ entity_table: string; entity_id: number; state: string }>(
      credentials,
      `/facts/${targetTable}/${targetId}/decision`,
      {
        method: "POST",
        body: JSON.stringify({ decision, comment }),
      },
    ),

  conflicts: (credentials: AdminCredentials) =>
    adminFetch<ConflictComparison[]>(credentials, "/conflicts"),

  annotateReconciliation: (
    credentials: AdminCredentials,
    reconciliationResultId: number,
    comment: string,
  ) =>
    adminFetch<{ entity_table: string; entity_id: number; state: string }>(
      credentials,
      `/reconciliation/${reconciliationResultId}/annotate`,
      {
        method: "POST",
        body: JSON.stringify({ to_state: "in_review", comment }),
      },
    ),

  rerunParse: (credentials: AdminCredentials, documentId: number) =>
    adminFetch<RerunParseResponse>(credentials, `/documents/${documentId}/rerun-parse`, {
      method: "POST",
    }),

  publishRelease: (
    credentials: AdminCredentials,
    payload: {
      dataset_name: string;
      release_version: string;
      release_notes: string;
      changelog_title: string;
      changelog_details: string;
    },
  ) =>
    adminFetch<ReleaseRecord>(credentials, "/releases/publish", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  releaseHistory: (credentials: AdminCredentials, datasetName?: string) =>
    adminFetch<ReleaseRecord[]>(credentials, "/releases/history", {}, { dataset_name: datasetName }),

  auditTrail: (credentials: AdminCredentials, params: FetchParams = {}) =>
    adminFetch<ReviewAction[]>(credentials, "/audit-trail", {}, params),

  uploadDocument: async (
    credentials: AdminCredentials,
    payload: {
      file: File;
      source_family: string;
      source_name: string;
      publication_date?: string;
      source_url?: string;
      notes?: string;
    },
  ): Promise<ManualUploadResponse> => {
    const form = new FormData();
    form.append("file", payload.file);
    form.append("source_family", payload.source_family);
    form.append("source_name", payload.source_name);
    if (payload.publication_date) form.append("publication_date", payload.publication_date);
    if (payload.source_url) form.append("source_url", payload.source_url);
    if (payload.notes) form.append("notes", payload.notes);

    const response = await fetch(buildUrl("/documents/upload"), {
      method: "POST",
      cache: "no-store",
      headers: {
        "X-Admin-Email": credentials.email,
        "X-Admin-Token": credentials.token,
      },
      body: form,
    });

    if (!response.ok) {
      let detail = `Upload failed with ${response.status}`;
      try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string") detail = payload.detail;
      } catch {
        // keep status-based message
      }
      const err = new Error(detail) as Error & { status: number };
      err.status = response.status;
      throw err;
    }

    return (await response.json()) as ManualUploadResponse;
  },

  triggerScraper: (credentials: AdminCredentials) =>
    adminFetch<{ status: string; task: string }>(credentials, "/scraper/trigger", {
      method: "POST",
    }),

  scraperStatus: (credentials: AdminCredentials) =>
    adminFetch<ScraperStatusResponse>(credentials, "/scraper/status"),

  debtSummary: (credentials: AdminCredentials) =>
    adminFetch<DebtSummaryResponse>(credentials, "/debt/summary"),
};

export type ScraperRun = {
  id: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  response_headers_json: string | null;
  requested_url: string;
};

export type ScraperStatusResponse = {
  source_name: string;
  task_name: string;
  runs: ScraperRun[];
};

export type DebtSummaryBucket = {
  label: string;
  amount: string;
};

export type DebtSummaryResponse = {
  total_outstanding_inr_crore: string;
  instruments_authoritative: number;
  instruments_computed: number;
  buckets: DebtSummaryBucket[];
  last_reconciliation: {
    id: number | null;
    name: string | null;
    status: string | null;
    started_at: string | null;
    completed_at: string | null;
    scope_json: string | null;
  };
};
