import type { Metadata } from "next";
import { api } from "@/lib/api";
import { LastUpdated } from "@/components/ui/last-updated";
import { PageError } from "@/components/ui/page-error";
import { DebtStackTable } from "./debt-stack-table";

export const metadata: Metadata = { title: "Debt Stack — AP SDL Instruments" };

const fmtCrore = (v: number | null) =>
  v != null
    ? "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr"
    : "—";

const fmtLakhCrore = (v: number | null) =>
  v != null ? "₹" + (v / 100000).toFixed(2) + " L Cr" : "—";

interface Props {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function DebtStackPage({ searchParams }: Props) {
  const resolvedParams = await searchParams;

  const page =
    typeof resolvedParams.page === "string" ? parseInt(resolvedParams.page, 10) || 1 : 1;
  const search = typeof resolvedParams.search === "string" ? resolvedParams.search : undefined;
  const sortBy =
    typeof resolvedParams.sort_by === "string"
      ? (resolvedParams.sort_by as "maturity_date" | "issue_date" | "coupon_rate" | "outstanding_principal" | "nomenclature")
      : "maturity_date";
  const sortOrder =
    typeof resolvedParams.sort_order === "string"
      ? (resolvedParams.sort_order as "asc" | "desc")
      : "asc";

  const result = await api.debt.stack({
    state_code: "AP",
    page,
    page_size: 50,
    search,
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  const now = new Date().toISOString();

  if (!result) return <PageError retryHref="/debt-stack" />;

  const agg = result.aggregates_for_state;

  return (
    <div className="space-y-6">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Debt Stack</h1>
          <p className="mt-1 text-slate-500">
            Andhra Pradesh — per-instrument State Development Loans (SDLs)
          </p>
          <LastUpdated timestamp={now} className="mt-1" />
        </div>
        <span className="inline-flex items-center rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
          Source: RBI Outstanding Securities
        </span>
      </div>

      {/* ── Aggregates ────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-600">Total Instruments</p>
          <p className="mt-3 text-2xl font-semibold tracking-tight text-ink">
            {agg.total_instruments.toLocaleString("en-IN")}
          </p>
          <p className="mt-1 text-xs text-slate-400">Active SDL issuances</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-600">Total Outstanding</p>
          <p className="mt-3 text-2xl font-semibold tracking-tight text-ink">
            {fmtLakhCrore(agg.total_outstanding_inr_crore)}
          </p>
          <p className="mt-1 text-xs text-slate-400">Principal outstanding</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-600">Avg. Coupon Rate</p>
          <p className="mt-3 text-2xl font-semibold tracking-tight text-ink">
            {agg.weighted_average_coupon != null
              ? `${agg.weighted_average_coupon.toFixed(2)}%`
              : "—"}
          </p>
          <p className="mt-1 text-xs text-slate-400">Weighted average</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-600">Maturity Range</p>
          <p className="mt-3 text-sm font-semibold tracking-tight text-ink">
            {agg.earliest_maturity ?? "—"}
            <span className="mx-1 text-slate-400">→</span>
            {agg.latest_maturity ?? "—"}
          </p>
          <p className="mt-1 text-xs text-slate-400">Earliest to latest maturity</p>
        </div>
      </div>

      {/* ── Searchable Table (client component) ───────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 shadow-sm overflow-hidden">
        <div className="border-b border-slate-100 px-6 py-4">
          <h2 className="text-base font-semibold text-slate-800">All SDL Instruments</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {result.pagination.total.toLocaleString("en-IN")} instruments total ·{" "}
            showing page {result.pagination.page} of{" "}
            {Math.ceil(result.pagination.total / result.pagination.page_size)}
          </p>
        </div>
        <DebtStackTable
          data={result.data}
          pagination={result.pagination}
          currentSearch={search ?? ""}
          currentSort={sortBy}
          currentOrder={sortOrder}
        />
      </div>

      {/* ── Notes ─────────────────────────────────────────────────── */}
      <div className="rounded-xl bg-slate-50 border border-slate-200 px-5 py-4 text-xs text-slate-500 space-y-1">
        <p className="font-semibold text-slate-600">Notes</p>
        <p>• Data sourced from RBI Outstanding State Government Securities dataset.</p>
        <p>• Outstanding principal is as of the RBI reporting date (May 2026).</p>
        <p>• ISIN = International Securities Identification Number (unique per issuance).</p>
        <p>• YTM = Years to Maturity from the as-of date.</p>
      </div>
    </div>
  );
}
