import type {
  ApiHealthResponse,
  ChangelogEntry,
  MetricObservation,
  MetricSeries,
} from "@public-finance/shared-ts";
import { buildApiUrl } from "./api-url";

export type { ApiHealthResponse, ChangelogEntry, MetricObservation, MetricSeries };

// ─── Response shapes ───────────────────────────────────────────────────────────

export interface ApiListResponse {
  data: Record<string, unknown>[];
  pagination: { page: number; page_size: number; total: number };
  sort: { by: string; order: string };
}

export interface DebtDataPoint {
  fiscal_year: string;
  value: number;
}

export interface DebtYoYPoint {
  fiscal_year: string;
  outstanding: number;
  increase: number;
  increase_pct: number;
}

export interface DebtSummaryResponse {
  current_outstanding: DebtDataPoint | null;
  historical_outstanding: DebtDataPoint[];
  year_over_year: DebtYoYPoint[];
  breakdown: Record<string, DebtDataPoint[]>;
}

export interface DebtMaturityPoint {
  fiscal_year: string;
  principal_due: number;
  instrument_count: number;
}

export interface DebtMaturityResponse {
  schedule: DebtMaturityPoint[];
  total: number;
}

// ─── State Overview shapes (Phase 2 redesign) ─────────────────────────────────

export interface HeadlineMetric {
  metric_code: string;
  label: string;
  metric_name?: string;
  value: number | null;
  unit?: string;
  unit_scale?: string;
  basis_tag?: string;
  fiscal_year?: string;
  period_start?: string;
  period_end?: string;
}

export interface HeadlineResponse {
  state_code: string;
  metrics: HeadlineMetric[];
  derived: Record<string, number>;
}

export interface DebtCompositionComponent {
  metric_code: string;
  label: string;
  value: number | null;
  basis_tag: string;
}

export interface DebtCompositionResponse {
  state_code: string;
  fiscal_year: string | null;
  total: number | null;
  components: DebtCompositionComponent[];
}

export interface MaturityProfilePoint {
  fiscal_year: string;
  principal_due: number | null;
  pct_of_total: number | null;
}

export interface MaturityProfileResponse {
  state_code: string;
  schedule: MaturityProfilePoint[];
  total_principal: number;
}

export interface DebtStackInstrument {
  isin: string;
  nomenclature: string;
  issuer_name: string;
  issuer_state_code: string | null;
  coupon_rate: number | null;
  issue_date: string | null;
  maturity_date: string | null;
  years_to_maturity: number | null;
  outstanding_principal: number | null;
  as_of_date: string | null;
}

export interface DebtStackAggregates {
  total_instruments: number;
  total_outstanding_inr_crore: number | null;
  weighted_average_coupon: number | null;
  earliest_maturity: string | null;
  latest_maturity: string | null;
}

export interface DebtStackResponse {
  data: DebtStackInstrument[];
  pagination: { page: number; page_size: number; total: number };
  sort: { by: string; order: string };
  filters_applied: Record<string, unknown>;
  aggregates_for_state: DebtStackAggregates;
}

export interface DebtStackFilters {
  state_code?: string;
  maturity_after?: string;
  maturity_before?: string;
  coupon_min?: number;
  coupon_max?: number;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: "maturity_date" | "issue_date" | "coupon_rate" | "outstanding_principal" | "nomenclature";
  sort_order?: "asc" | "desc";
}

export interface PeerSnapshotRow {
  state_code: string;
  metric_code: string;
  metric_name: string;
  value: number | null;
  unit: string;
  unit_scale: string;
  basis_tag: string;
  fiscal_year: string;
  period_start: string;
  period_end: string;
}

export interface PeerSnapshotResponse {
  metric_code: string;
  fiscal_year: string;
  states_requested: string[];
  data: PeerSnapshotRow[];
}

export interface PeerSeriesPoint {
  fiscal_year: string;
  value: number | null;
  basis_tag: string;
}

export interface PeerSeriesResponse {
  metric_code: string;
  metric_name: string;
  unit_scale: string;
  states_requested: string[];
  series: Record<string, PeerSeriesPoint[]>;
}

export interface PeerMetricCatalogEntry {
  metric_code: string;
  metric_name: string;
  metric_group: string;
  unit_scale: string;
  state_count: number;
}

export interface PeerMetricCatalogResponse {
  metrics: PeerMetricCatalogEntry[];
}

// ─── Filter shapes ─────────────────────────────────────────────────────────────

export interface CommonFilters {
  state_code?: string;
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

async function apiFetch<T>(path: string, params: FetchParams = {}): Promise<T | null> {
  try {
    const url = buildApiUrl(path, params);
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// Returns the URL for a CSV download of the full dataset (no pagination limit)
export function csvDownloadUrl(apiPath: string, filters: FetchParams = {}): string {
  return buildApiUrl(`/api/v1${apiPath}`, { ...filters, format: "csv", page_size: 2000 });
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
    summary: (state_code = "AP") =>
      apiFetch<DebtSummaryResponse>("/api/v1/debt/summary", { state_code }),
    maturitySchedule: (state_code = "AP") =>
      apiFetch<DebtMaturityResponse>("/api/v1/debt/maturity-schedule", { state_code }),
    stack: (filters: DebtStackFilters = {}) =>
      apiFetch<DebtStackResponse>("/api/v1/debt/stack", filters as FetchParams),
  },

  ap: {
    headline: (state_code = "AP") =>
      apiFetch<HeadlineResponse>("/api/v1/ap/headline", { state_code }),
    debtComposition: (state_code = "AP", fiscal_year?: string) =>
      apiFetch<DebtCompositionResponse>(
        "/api/v1/ap/debt-composition",
        fiscal_year ? { state_code, fiscal_year } : { state_code }
      ),
    maturityProfile: (state_code = "AP") =>
      apiFetch<MaturityProfileResponse>("/api/v1/ap/maturity-profile", { state_code }),
  },

  peers: {
    compareSnapshot: (metric_code: string, states: string[], fiscal_year: string, basis?: string) =>
      apiFetch<PeerSnapshotResponse>(
        `/api/v1/peer-comparison/${encodeURIComponent(metric_code)}`,
        { states: states.join(","), fiscal_year, ...(basis ? { basis } : {}) }
      ),
    compareSeries: (metric_code: string, states: string[], basis?: string) =>
      apiFetch<PeerSeriesResponse>(
        `/api/v1/peer-comparison/${encodeURIComponent(metric_code)}`,
        { states: states.join(","), ...(basis ? { basis } : {}) }
      ),
    metricCatalog: () =>
      apiFetch<PeerMetricCatalogResponse>("/api/v1/peer-comparison/_metrics/catalog"),
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
