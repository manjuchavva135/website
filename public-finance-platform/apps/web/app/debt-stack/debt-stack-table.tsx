"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useState, useTransition } from "react";
import type { DebtStackInstrument } from "@/lib/api";

interface Props {
  data: DebtStackInstrument[];
  pagination: { page: number; page_size: number; total: number };
  currentSearch: string;
  currentSort: string;
  currentOrder: "asc" | "desc";
}

const fmtCrore = (v: number | null) =>
  v != null
    ? "\u20b9" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr"
    : "\u2014";

const SORT_COLS: { key: string; label: string }[] = [
  { key: "nomenclature", label: "Name" },
  { key: "coupon_rate", label: "Coupon %" },
  { key: "issue_date", label: "Issued" },
  { key: "maturity_date", label: "Matures" },
  { key: "outstanding_principal", label: "Outstanding" },
];

export function DebtStackTable({
  data,
  pagination,
  currentSearch,
  currentSort,
  currentOrder,
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [searchInput, setSearchInput] = useState(currentSearch);

  const createUrl = useCallback(
    (overrides: Record<string, string | number | undefined>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(overrides)) {
        if (v === undefined || v === "") {
          params.delete(k);
        } else {
          params.set(k, String(v));
        }
      }
      return `${pathname}?${params.toString()}`;
    },
    [pathname, searchParams]
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    startTransition(() => {
      router.push(createUrl({ search: searchInput, page: 1 }));
    });
  };

  const handleSort = (col: string) => {
    const nextOrder =
      currentSort === col ? (currentOrder === "asc" ? "desc" : "asc") : "asc";
    startTransition(() => {
      router.push(createUrl({ sort_by: col, sort_order: nextOrder, page: 1 }));
    });
  };

  const handlePage = (p: number) => {
    startTransition(() => {
      router.push(createUrl({ page: p }));
    });
  };

  const totalPages = Math.ceil(pagination.total / pagination.page_size);

  const SortIcon = ({ col }: { col: string }) => {
    if (currentSort !== col) return <span className="text-slate-300 ml-1">↕</span>;
    return <span className="text-tide ml-1">{currentOrder === "asc" ? "↑" : "↓"}</span>;
  };

  return (
    <div className={isPending ? "opacity-60 transition-opacity" : ""}>
      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-2 px-6 py-4 border-b border-slate-100">
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by ISIN or name…"
          className="flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-tide focus:outline-none focus:ring-1 focus:ring-tide/30"
        />
        <button
          type="submit"
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-tide"
        >
          Search
        </button>
        {currentSearch && (
          <button
            type="button"
            onClick={() => {
              setSearchInput("");
              startTransition(() => router.push(createUrl({ search: undefined, page: 1 })));
            }}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-400 hover:text-slate-600"
          >
            ✕
          </button>
        )}
      </form>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs text-slate-600">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/70">
              <th className="py-2.5 pl-6 pr-4 text-left font-semibold text-slate-700">ISIN</th>
              {SORT_COLS.map((col) => (
                <th
                  key={col.key}
                  className="py-2.5 pr-4 text-right font-semibold text-slate-700 cursor-pointer hover:text-tide select-none whitespace-nowrap"
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  <SortIcon col={col.key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-400">
                  No instruments found
                </td>
              </tr>
            )}
            {data.map((row) => (
              <tr
                key={row.isin}
                className="border-b border-slate-50 hover:bg-slate-50/60"
              >
                <td className="py-2 pl-6 pr-4 font-mono text-[11px] text-slate-500">
                  {row.isin}
                </td>
                <td className="py-2 pr-4 text-right text-slate-700 max-w-xs truncate">
                  {row.nomenclature}
                </td>
                <td className="py-2 pr-4 text-right font-medium">
                  {row.coupon_rate != null ? `${row.coupon_rate.toFixed(2)}%` : "—"}
                </td>
                <td className="py-2 pr-4 text-right">
                  {row.issue_date ?? "—"}
                </td>
                <td className="py-2 pr-4 text-right">
                  <span
                    className={
                      row.years_to_maturity != null && row.years_to_maturity <= 1
                        ? "font-semibold text-rose-600"
                        : row.years_to_maturity != null && row.years_to_maturity <= 3
                          ? "font-medium text-amber-600"
                          : ""
                    }
                  >
                    {row.maturity_date ?? "—"}
                    {row.years_to_maturity != null && (
                      <span className="ml-1 text-slate-400">
                        ({row.years_to_maturity.toFixed(1)}y)
                      </span>
                    )}
                  </span>
                </td>
                <td className="py-2 pr-6 text-right font-medium">
                  {fmtCrore(row.outstanding_principal)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 text-xs text-slate-500">
        <span>
          {pagination.total.toLocaleString("en-IN")} instruments · page {pagination.page} of{" "}
          {totalPages}
        </span>
        <div className="flex gap-1">
          <button
            disabled={pagination.page <= 1}
            onClick={() => handlePage(pagination.page - 1)}
            className="rounded px-2 py-1 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            ←
          </button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            const start = Math.max(1, Math.min(pagination.page - 2, totalPages - 4));
            const p = start + i;
            return (
              <button
                key={p}
                onClick={() => handlePage(p)}
                className={`rounded px-2 py-1 ${
                  p === pagination.page
                    ? "bg-tide/10 font-medium text-tide"
                    : "hover:bg-slate-100"
                }`}
              >
                {p}
              </button>
            );
          })}
          <button
            disabled={pagination.page >= totalPages}
            onClick={() => handlePage(pagination.page + 1)}
            className="rounded px-2 py-1 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
