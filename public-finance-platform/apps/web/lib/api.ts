import type {
  ApiHealthResponse,
  ChangelogEntry,
  MetricObservation,
  MetricSeries,
} from "@public-finance/shared-ts";

export type { ApiHealthResponse, ChangelogEntry, MetricObservation, MetricSeries };

// ─── Response shapes ───────────────────────────────────────────────────────────

export interface ApiListResponse {
  data: Record<string, unknown>[];
  pagination: { page: number; page_size: number; total: number };
  sort: { by: string; order: string };
}

// ─── Filter shapes ─────────────────────────────────────────────────────────────

export interface CommonFilters {
  financial_year?: string;
  basis?: string;
  period_type?: string;
  department?: string;
  start_date?: string;
  end_date?: string;
  as_of?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

type FetchParams = Record<string, string | number | boolean | null | undefined>;

// ─── Internals ─────────────────────────────────────────────────────────────────

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function buildUrl(path: string, params: FetchParams): string {
  const url = new URL(path, BASE);
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function apiFetch<T>(path: string, params: FetchParams = {}): Promise<T | null> {
  try {
    const url = buildUrl(path, params);
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// Returns the URL for a CSV download of the full dataset (no pagination limit)
export function csvDownloadUrl(apiPath: string, filters: FetchParams = {}): string {
  return buildUrl(`/api/v1${apiPath}`, { ...filters, format: "csv", page_size: 2000 });
}

// ─── Public API client ─────────────────────────────────────────────────────────

export const api = {
  health: () => apiFetch<ApiHealthResponse>("/api/v1/health"),

  metrics: {
    list: () => apiFetch<MetricSeries[]>("/api/v1/metrics"),
    observations: (slug: string, limit = 50) =>
      apiFetch<MetricObservation[]>(`/api/v1/metrics/${slug}/observations`, { limit }),
  },

  debt: {
    outstanding: (f: CommonFilters = {}) =>
      apiFetch<ApiListResponse>("/api/v1/debt/outstanding", f as FetchParams),
    issues: (f: CommonFilters = {}) =>
      apiFetch<ApiListResponse>("/api/v1/debt/issues", f as FetchParams),
    pipeline: (f: CommonFilters = {}) =>
      apiFetch<ApiListResponse>("/api/v1/debt/pipeline", f as FetchParams),
    repayments: (f: CommonFilters = {}) =>
      apiFetch<ApiListResponse>("/api/v1/debt/repayments", f as FetchParams),
  },

  fiscal: {
    receipts: (f: CommonFilters = {}) =>
      apiFetch<ApiListResponse>("/api/v1/fiscal/receipts", f as FetchParams),
    expenditure: (f: CommonFilters = {}) =>
      apiFetch<ApiListResponse>("/api/v1/fiscal/expenditure", f as FetchParams),
    deficits: (f: CommonFilters = {}) =>
      apiFetch<ApiListResponse>("/api/v1/fiscal/deficits", f as FetchParams),
  },

  departments: {
    spending: (f: CommonFilters = {}) =>
      apiFetch<ApiListResponse>("/api/v1/departments/spending", f as FetchParams),
  },

  sources: (
    f: {
      financial_year?: string;
      start_date?: string;
      end_date?: string;
      page?: number;
      page_size?: number;
    } = {}
  ) => apiFetch<ApiListResponse>("/api/v1/sources", f as FetchParams),

  releases: (f: { page?: number; page_size?: number } = {}) =>
    apiFetch<ApiListResponse>("/api/v1/releases", f as FetchParams),

  changelog: () => apiFetch<ChangelogEntry[]>("/api/v1/changelog"),

  provenance: (observationId: number) =>
    apiFetch<unknown>(`/api/v1/provenance/${observationId}`),
};
