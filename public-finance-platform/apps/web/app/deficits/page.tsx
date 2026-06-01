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
import { PeerCompareToggle } from "@/components/ui/peer-compare-toggle";
import { StoryDataLayout } from "@/components/layout/story-data-layout";
import { TimeSeriesChart } from "@/components/charts/time-series-chart";
import type { TimeSeriesPoint } from "@/components/charts/time-series-chart";

export const metadata: Metadata = { title: "Deficits" };

const fmtCrore = (v: number) =>
  "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function DeficitsPage({ searchParams }: Props) {
  const resolvedParams = await searchParams;
  const filters = parseCommonFilters(resolvedParams);
  const [result, headline] = await Promise.all([
    api.fiscal.deficits(filters),
    api.ap.headline(),
  ]);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis;

  const metrics = headline?.metrics ?? [];
  const fiscalDeficit = metrics.find((m) => m.metric_code === "gross_fiscal_deficit");
  const revenueDeficit = metrics.find((m) => m.metric_code === "revenue_deficit");
  const interestPayments = metrics.find((m) => m.metric_code === "interest_payments_gross");

  // Build time-series chart
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

  const storyContent = (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          title="Gross Fiscal Deficit"
          value={fiscalDeficit?.value != null ? fmtCrore(fiscalDeficit.value) : null}
          basis={fiscalDeficit?.basis_tag}
          description={fiscalDeficit?.fiscal_year ? `FY ${fiscalDeficit.fiscal_year}` : undefined}
          lastUpdated={fiscalDeficit ? now : null}
        />
        <MetricCard
          title="Revenue Deficit"
          value={revenueDeficit?.value != null ? fmtCrore(revenueDeficit.value) : null}
          basis={revenueDeficit?.basis_tag}
          description={revenueDeficit?.fiscal_year ? `FY ${revenueDeficit.fiscal_year}` : undefined}
          lastUpdated={revenueDeficit ? now : null}
        />
        <MetricCard
          title="Interest Payments"
          value={interestPayments?.value != null ? fmtCrore(interestPayments.value) : null}
          basis={interestPayments?.basis_tag}
          description={interestPayments?.fiscal_year ? `FY ${interestPayments.fiscal_year}` : undefined}
          lastUpdated={interestPayments ? now : null}
        />
      </div>

      {/* Trend chart */}
      {chartData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-600">Deficit Trends</h2>
          <TimeSeriesChart
            data={chartData}
            seriesKeys={seriesKeys.length > 0 ? seriesKeys : ["amount"]}
            yLabel="₹ Crore"
          />
        </div>
      )}

      {/* Peer comparison */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">AP vs Peers</h2>
        <p className="mb-4 text-xs text-slate-500">
          Gross Fiscal Deficit compared with major states
        </p>
        <PeerCompareToggle
          metricCode="gross_fiscal_deficit"
          label="Fiscal Deficit (₹ Cr)"
          fiscalYear={fiscalDeficit?.fiscal_year ?? "2023-24"}
        />
      </div>
    </div>
  );

  const dataContent = (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Deficit Records</h2>
          {basis && <BasisBadge basis={basis} size="md" className="mt-1" />}
        </div>
      </div>
      {basis && <TrustCopy basis={basis} />}
      <FilterBar
        fields={["financial_year", "basis", "period_type", "start_date", "end_date"]}
        defaults={filters}
      />
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
    </>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Deficits</h1>
          <p className="mt-1 text-slate-500">
            Fiscal, revenue and primary deficit — time-series with peer comparison
          </p>
          <LastUpdated timestamp={result ? now : null} className="mt-1" />
        </div>
      </div>
      <StoryDataLayout story={storyContent} data={dataContent} />
    </div>
  );
}

