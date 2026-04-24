import type { CommonFilters } from "./api";

export const FINANCIAL_YEARS = [
  "2025-26",
  "2024-25",
  "2023-24",
  "2022-23",
  "2021-22",
  "2020-21",
  "2019-20",
  "2018-19",
  "2017-18",
  "2016-17",
];

export const BASIS_OPTIONS = [
  { value: "audited_actual", label: "Audited Actuals" },
  { value: "actual", label: "Actual" },
  { value: "monthly_actual_provisional", label: "Monthly Provisional" },
  { value: "quarter_actual", label: "Quarter Actual" },
  { value: "budget_estimate", label: "Budget Estimate" },
  { value: "revised_estimate", label: "Revised Estimate" },
  { value: "projection", label: "Projection" },
  { value: "scheduled", label: "Scheduled" },
  { value: "notified", label: "Notified" },
  { value: "issued", label: "Issued" },
  { value: "due", label: "Due" },
  { value: "paid", label: "Paid" },
  { value: "nowcast", label: "Nowcast" },
] as const;

type RawSearchParams = Record<string, string | string[] | undefined>;

function str(p: RawSearchParams, key: string): string | undefined {
  const v = p[key];
  return typeof v === "string" ? v : undefined;
}

function num(p: RawSearchParams, key: string, fallback: number): number {
  const v = str(p, key);
  if (!v) return fallback;
  const n = parseInt(v, 10);
  return isNaN(n) ? fallback : n;
}

export function parseCommonFilters(searchParams: RawSearchParams): CommonFilters {
  return {
    financial_year: str(searchParams, "financial_year"),
    basis: str(searchParams, "basis"),
    period_type: str(searchParams, "period_type"),
    department: str(searchParams, "department"),
    start_date: str(searchParams, "start_date"),
    end_date: str(searchParams, "end_date"),
    as_of: str(searchParams, "as_of"),
    page: num(searchParams, "page", 1),
    page_size: num(searchParams, "page_size", 50),
    sort_by: str(searchParams, "sort_by"),
    sort_order: (str(searchParams, "sort_order") as "asc" | "desc") ?? "desc",
  };
}

export function buildFilterUrl(
  pathname: string,
  filters: Record<string, string | number | boolean | undefined | null>
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "") continue;
    if (key === "page" && value === 1) continue;
    if (key === "page_size" && value === 50) continue;
    if (key === "sort_order" && value === "desc") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${pathname}?${qs}` : pathname;
}

/** Returns the active basis found across a set of data rows. */
export function detectBasis(rows: Record<string, unknown>[]): string | undefined {
  for (const row of rows.slice(0, 5)) {
    const b = row["basis_tag"] ?? row["basis"];
    if (typeof b === "string" && b) return b;
  }
  return undefined;
}

export function lastUpdatedFromRows(rows: Record<string, unknown>[]): string | null {
  const dateKeys = [
    "last_updated",
    "updated_at",
    "published_at",
    "created_at",
    "as_of_date",
    "event_date",
    "period_end",
    "publication_date",
  ];
  for (const row of rows) {
    for (const key of dateKeys) {
      const value = row[key];
      if (typeof value === "string" && value.trim().length > 0) {
        return value;
      }
    }
  }
  return null;
}
