"use client";

import { useState, useCallback } from "react";
import { BasisBadge } from "@/components/ui/basis-badge";
import { downloadCsv } from "@/lib/csv-export";

// ─── Helpers ───────────────────────────────────────────────────────────────────

function isDateKey(key: string): boolean {
  return /date|_at|_on/.test(key.toLowerCase());
}

function isAmountKey(key: string): boolean {
  return /amount|outstanding|principal|expenditure|receipt|deficit|coupon|sanctioned|actual/.test(
    key.toLowerCase()
  );
}

function isBasisKey(key: string): boolean {
  return key === "basis" || key === "basis_tag";
}

function formatCell(key: string, value: unknown): React.ReactNode {
  if (value === null || value === undefined) return <span className="text-slate-300">—</span>;
  if (isBasisKey(key)) return <BasisBadge basis={String(value)} />;
  if (isAmountKey(key) && !isNaN(Number(value))) {
    return (
      <span className="font-mono tabular-nums">
        {Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
      </span>
    );
  }
  if (isDateKey(key)) {
    const d = new Date(String(value));
    return isNaN(d.getTime()) ? String(value) : d.toLocaleDateString("en-IN");
  }
  return String(value);
}

function prettyHeader(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Props ─────────────────────────────────────────────────────────────────────

interface Pagination {
  page: number;
  page_size: number;
  total: number;
}

interface DataTableProps {
  data: Record<string, unknown>[];
  pagination?: Pagination;
  csvFilename?: string;
  /** Direct CSV download URL (API-side CSV with all pages) */
  csvHref?: string;
  /** Columns to show; auto-detected from data if omitted */
  columns?: string[];
  onPageChange?: (page: number) => void;
  caption?: string;
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function DataTable({
  data,
  pagination,
  csvFilename = "export",
  csvHref,
  columns,
  onPageChange,
  caption,
}: DataTableProps) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  // Determine columns – exclude internal keys starting with _
  const cols =
    columns ??
    (data.length > 0
      ? Object.keys(data[0]).filter((k) => !k.startsWith("_"))
      : []);

  // Client-side sort of current page
  const sorted = useCallback(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      const cmp = String(av).localeCompare(String(bv), "en", { numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const rows = sorted();

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const totalPages = pagination
    ? Math.ceil(pagination.total / pagination.page_size)
    : 1;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/80 shadow-sm backdrop-blur">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <span className="text-sm text-slate-500">
          {pagination
            ? `${pagination.total.toLocaleString("en-IN")} records`
            : `${data.length} rows`}
        </span>
        <div className="flex gap-2">
          {csvHref && (
            <a
              href={csvHref}
              download
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              title="Download full dataset as CSV"
            >
              ↓ Download all (CSV)
            </a>
          )}
          <button
            onClick={() => downloadCsv(csvFilename, rows)}
            className="rounded-lg border border-tide bg-tide/10 px-3 py-1.5 text-xs font-medium text-teal-700 hover:bg-tide/20"
            title="Export current page as CSV"
          >
            ↓ Export page (CSV)
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm" aria-label={caption ?? "Data table"}>
          {caption && <caption className="sr-only">{caption}</caption>}
          <thead>
            <tr className="bg-slate-50 text-left">
              {cols.map((col) => (
                <th
                  key={col}
                  className="cursor-pointer whitespace-nowrap px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500 hover:text-slate-700"
                  onClick={() => toggleSort(col)}
                  aria-sort={
                    sortKey === col
                      ? sortDir === "asc"
                        ? "ascending"
                        : "descending"
                      : undefined
                  }
                >
                  {prettyHeader(col)}
                  {sortKey === col && (
                    <span className="ml-1 text-tide">{sortDir === "asc" ? "↑" : "↓"}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, ri) => (
              <tr key={ri} className="hover:bg-slate-50/60">
                {cols.map((col) => (
                  <td key={col} className="px-4 py-2.5 text-slate-700">
                    {formatCell(col, row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
          <span>
            Page {pagination.page} of {totalPages}
          </span>
          <div className="flex gap-2">
            {pagination.page > 1 && onPageChange && (
              <button
                onClick={() => onPageChange(pagination.page - 1)}
                className="rounded-lg border border-slate-200 px-3 py-1 text-xs hover:bg-slate-50"
              >
                ← Prev
              </button>
            )}
            {pagination.page < totalPages && onPageChange && (
              <button
                onClick={() => onPageChange(pagination.page + 1)}
                className="rounded-lg border border-slate-200 px-3 py-1 text-xs hover:bg-slate-50"
              >
                Next →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
