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
import { TimeSeriesChart } from "@/components/charts/time-series-chart";
import type { TimeSeriesPoint } from "@/components/charts/time-series-chart";

export const metadata: Metadata = { title: "Deficits" };

type Props = { searchParams: Record<string, string | string[] | undefined> };

export default async function DeficitsPage({ searchParams }: Props) {
  const filters = parseCommonFilters(searchParams);
  const result = await api.fiscal.deficits(filters);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis;

  // Build time-series chart separating different deficit types
  const byPeriod = new Map<string, Record<string, number>>();
  for (const row of result?.data ?? []) {
    const label =
      (row["period_label"] as string) ??
      (row["period_start"] as string)?.slice(0, 7) ??
      "—";
    if (!byPeriod.has(label)) byPeriod.set(label, {});
    const metricKey = String(row["metric_name"] ?? row["category"] ?? "deficit").replace(/\s+/g, "_");
    byPeriod.get(label)![metricKey] = (byPeriod.get(label)![metricKey] ?? 0) + Number(row["amount"] ?? 0);
  }

  const chartData: TimeSeriesPoint[] = [...byPeriod.entries()]
    .filter(([label]) => label !== "—")
    .slice(0, 24)
    .map(([label, vals]) => ({ label, ...vals }));

  const seriesKeys = [...new Set(chartData.flatMap((d) => Object.keys(d).filter((k) => k !== "label")))].slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Deficits</h1>
          <p className="mt-1 text-slate-500">
            Fiscal, revenue and primary deficit — time-series with basis labelling
          </p>
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
            title="Total Records"
            value={result.pagination.total}
            description="Deficit metric observations"
            basis={basis}
            lastUpdated={now}
          />
        </div>
      )}

      {result && result.data.length > 0 && chartData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-600">Deficit Trends</h2>
          <TimeSeriesChart
            data={chartData}
            seriesKeys={seriesKeys.length > 0 ? seriesKeys : ["amount"]}
            yLabel="₹ Crore"
          />
        </div>
      )}

      {!result && <PageError retryHref="/deficits" />}
      {result && result.data.length === 0 && (
        <EmptyState variant={filters.financial_year || filters.basis ? "filtered" : "no-data"} />
      )}
      {result && result.data.length > 0 && (
        <>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="fiscal-deficits"
            csvHref={csvDownloadUrl("/fiscal/deficits", filters as Record<string, string | number | boolean | null | undefined>)}
            caption="Fiscal deficits"
          />
          <ProvenanceDrawer rows={result.data} label="Deficit Provenance" />
        </>
      )}
    </div>
  );
}
