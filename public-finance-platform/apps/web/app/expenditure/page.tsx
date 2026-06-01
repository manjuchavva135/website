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

export const metadata: Metadata = { title: "Expenditure" };

const fmtCrore = (v: number) =>
  "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function ExpenditurePage({ searchParams }: Props) {
  const resolvedParams = await searchParams;
  const filters = parseCommonFilters(resolvedParams);
  const [result, headline] = await Promise.all([
    api.fiscal.expenditure(filters),
    api.ap.headline(),
  ]);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis;

  const metrics = headline?.metrics ?? [];
  const revExp = metrics.find((m) => m.metric_code === "revenue_expenditure_total");
  const devExp = metrics.find((m) => m.metric_code === "development_expenditure_total");
  const nonDevExp = metrics.find((m) => m.metric_code === "non_development_expenditure_total");

  const chartData: TimeSeriesPoint[] = (result?.data ?? [])
    .slice(0, 20)
    .map((row) => ({
      label:
        (row["period_label"] as string) ??
        (row["period_start"] as string)?.slice(0, 7) ??
        "—",
      amount: Number(row["amount"] ?? 0),
    }))
    .filter((d) => d.label !== "—");

  const storyContent = (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          title="Revenue Expenditure"
          value={revExp?.value != null ? fmtCrore(revExp.value) : null}
          basis={revExp?.basis_tag}
          description={revExp?.fiscal_year ? `FY ${revExp.fiscal_year}` : undefined}
          lastUpdated={revExp ? now : null}
        />
        <MetricCard
          title="Development Expenditure"
          value={devExp?.value != null ? fmtCrore(devExp.value) : null}
          basis={devExp?.basis_tag}
          description={devExp?.fiscal_year ? `FY ${devExp.fiscal_year}` : undefined}
          lastUpdated={devExp ? now : null}
        />
        <MetricCard
          title="Non-Development Expenditure"
          value={nonDevExp?.value != null ? fmtCrore(nonDevExp.value) : null}
          basis={nonDevExp?.basis_tag}
          description={nonDevExp?.fiscal_year ? `FY ${nonDevExp.fiscal_year}` : undefined}
          lastUpdated={nonDevExp ? now : null}
        />
      </div>

      {chartData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-600">Expenditure Over Time</h2>
          <TimeSeriesChart data={chartData} seriesKeys={["amount"]} yLabel="₹ Crore" />
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">AP vs Peers</h2>
        <p className="mb-4 text-xs text-slate-500">
          Revenue Expenditure compared with major states
        </p>
        <PeerCompareToggle
          metricCode="revenue_expenditure_total"
          label="Revenue Expenditure (₹ Cr)"
          fiscalYear={revExp?.fiscal_year ?? "2023-24"}
        />
      </div>
    </div>
  );

  const dataContent = (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Expenditure Records</h2>
          {basis && <BasisBadge basis={basis} size="md" className="mt-1" />}
        </div>
      </div>
      {basis && <TrustCopy basis={basis} />}
      <FilterBar
        fields={["financial_year", "basis", "period_type", "department", "start_date", "end_date"]}
        defaults={filters}
      />
      {!result && <PageError retryHref="/expenditure" />}
      {result && result.data.length === 0 && (
        <EmptyState variant={filters.financial_year || filters.basis ? "filtered" : "no-data"} />
      )}
      {result && result.data.length > 0 && (
        <>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="fiscal-expenditure"
            csvHref={csvDownloadUrl("/fiscal/expenditure", filters as Record<string, string | number | boolean | null | undefined>)}
            caption="Fiscal expenditure"
          />
          <ProvenanceDrawer rows={result.data} label="Expenditure Provenance" />
        </>
      )}
    </>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Expenditure</h1>
          <p className="mt-1 text-slate-500">
            Revenue and capital expenditure across major budget heads — with peer comparison
          </p>
          <LastUpdated timestamp={result ? now : null} className="mt-1" />
        </div>
      </div>
      <StoryDataLayout story={storyContent} data={dataContent} />
    </div>
  );
}
