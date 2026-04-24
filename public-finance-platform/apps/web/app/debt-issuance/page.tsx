import type { Metadata } from "next";
import { api, csvDownloadUrl } from "@/lib/api";
import { parseCommonFilters, detectBasis } from "@/lib/query-params";
import { FilterBar } from "@/components/data/filter-bar";
import { DataTable } from "@/components/data/data-table";
import { ProvenanceDrawer } from "@/components/provenance-drawer";
import { TrustCopy } from "@/components/ui/trust-copy";
import { BasisBadge } from "@/components/ui/basis-badge";
import { LastUpdated } from "@/components/ui/last-updated";
import { EmptyState } from "@/components/ui/empty-state";
import { PageError } from "@/components/ui/page-error";
import { MetricCard } from "@/components/ui/metric-card";
import { BarChartClient } from "@/components/charts/bar-chart-client";

export const metadata: Metadata = { title: "Debt Issuance" };

type Props = { searchParams: Record<string, string | string[] | undefined> };

export default async function DebtIssuancePage({ searchParams }: Props) {
  const filters = parseCommonFilters(searchParams);
  const result = await api.debt.issues(filters);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis;

  // Build chart data: issuance by period
  const chartData = (result?.data ?? [])
    .slice(0, 20)
    .map((row) => ({
      label:
        (row["period_label"] as string) ??
        (row["event_date"] as string)?.slice(0, 7) ??
        "—",
      amount: Number(row["amount_issued"] ?? row["amount"] ?? 0),
    }))
    .filter((d) => d.label !== "—");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Debt Issuance</h1>
          <p className="mt-1 text-slate-500">Confirmed debt issuances with instrument-level detail</p>
          <LastUpdated timestamp={result ? now : null} className="mt-1" />
        </div>
        {basis && <BasisBadge basis={basis} size="md" />}
      </div>

      {basis && <TrustCopy basis={basis} />}

      <FilterBar
        fields={["financial_year", "basis", "period_type", "start_date", "end_date"]}
        defaults={filters}
      />

      {result && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard
            title="Total Issuances"
            value={result.pagination.total}
            description="Matching debt issuance records"
            basis={basis}
            lastUpdated={now}
          />
        </div>
      )}

      {/* Chart */}
      {result && result.data.length > 0 && chartData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-600">Issuance by Period</h2>
          <BarChartClient data={chartData} dataKey="amount" yLabel="Amount" />
        </div>
      )}

      {!result && <PageError retryHref="/debt-issuance" />}
      {result && result.data.length === 0 && (
        <EmptyState variant={filters.financial_year || filters.basis ? "filtered" : "no-data"} />
      )}
      {result && result.data.length > 0 && (
        <>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="debt-issuances"
            csvHref={csvDownloadUrl("/debt/issues", filters as Record<string, string | number | boolean | null | undefined>)}
            caption="Debt issuance records"
          />
          <ProvenanceDrawer rows={result.data} label="Issuance Provenance" />
        </>
      )}
    </div>
  );
}
