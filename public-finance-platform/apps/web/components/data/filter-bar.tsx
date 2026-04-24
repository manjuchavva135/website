"use client";

import { Suspense } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { FINANCIAL_YEARS, BASIS_OPTIONS, buildFilterUrl } from "@/lib/query-params";
import type { CommonFilters } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

type FieldName =
  | "financial_year"
  | "basis"
  | "period_type"
  | "department"
  | "start_date"
  | "end_date"
  | "as_of";

interface FilterBarProps {
  /** Which filter fields to render */
  fields?: FieldName[];
  defaults?: CommonFilters;
  /** Extra department options to show */
  departments?: string[];
}

// ─── Inner component (uses useSearchParams) ───────────────────────────────────

function FilterBarInner({ fields, defaults, departments = [] }: FilterBarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function current(key: string): string {
    return searchParams.get(key) ?? (defaults as Record<string, unknown>)?.[key]?.toString() ?? "";
  }

  const visibleFields: FieldName[] = fields ?? [
    "financial_year",
    "basis",
    "start_date",
    "end_date",
  ];

  function applyFilters(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const next: Record<string, string> = {};
    for (const field of visibleFields) {
      const val = fd.get(field);
      if (val && String(val) !== "") next[field] = String(val);
    }
    router.push(buildFilterUrl(pathname, next));
  }

  function reset() {
    router.push(pathname);
  }

  const sharedInput =
    "rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-tide/40";

  return (
    <form
      onSubmit={applyFilters}
      className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white/70 px-4 py-3 backdrop-blur"
      role="search"
      aria-label="Filter data"
    >
      {visibleFields.includes("financial_year") && (
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Financial Year</span>
          <select name="financial_year" defaultValue={current("financial_year")} className={sharedInput}>
            <option value="">All years</option>
            {FINANCIAL_YEARS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
      )}

      {visibleFields.includes("basis") && (
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Basis</span>
          <select name="basis" defaultValue={current("basis")} className={sharedInput}>
            <option value="">All bases</option>
            {BASIS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      )}

      {visibleFields.includes("department") && (
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Department</span>
          <select name="department" defaultValue={current("department")} className={sharedInput}>
            <option value="">All departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
      )}

      {visibleFields.includes("period_type") && (
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">Period</span>
          <select name="period_type" defaultValue={current("period_type")} className={sharedInput}>
            <option value="">All periods</option>
            <option value="annual">Annual</option>
            <option value="half_year">Half-year</option>
            <option value="quarter">Quarter</option>
            <option value="month">Month</option>
          </select>
        </label>
      )}

      {visibleFields.includes("start_date") && (
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">From</span>
          <input
            type="date"
            name="start_date"
            defaultValue={current("start_date")}
            className={sharedInput}
          />
        </label>
      )}

      {visibleFields.includes("end_date") && (
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">To</span>
          <input
            type="date"
            name="end_date"
            defaultValue={current("end_date")}
            className={sharedInput}
          />
        </label>
      )}

      {visibleFields.includes("as_of") && (
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-500">As of</span>
          <input
            type="date"
            name="as_of"
            defaultValue={current("as_of")}
            className={sharedInput}
          />
        </label>
      )}

      <div className="flex gap-2">
        <button
          type="submit"
          className="rounded-lg bg-tide px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-600 focus:outline-none focus:ring-2 focus:ring-tide/50"
        >
          Apply
        </button>
        <button
          type="button"
          onClick={reset}
          className="rounded-lg border border-slate-200 bg-white px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Reset
        </button>
      </div>
    </form>
  );
}

// ─── Public export (wraps inner in Suspense) ──────────────────────────────────

export function FilterBar(props: FilterBarProps) {
  return (
    <Suspense
      fallback={
        <div className="h-16 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
      }
    >
      <FilterBarInner {...props} />
    </Suspense>
  );
}
