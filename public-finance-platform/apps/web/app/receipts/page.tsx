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

export const metadata: Metadata = { title: "Receipts" };

const fmtCrore = (v: number) =>
  "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function ReceiptsPage({ searchParams }: Props) {
  const resolvedParams = await searchParams;
  const filters = parseCommonFilters(resolvedParams);
  const [result, headline] = await Promise.all([
    api.fiscal.receipts(filters),
    api.ap.headline(),
  ]);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis;

  const metrics = headline?.metrics ?? [];
  const revReceipts = metrics.find((m) => m.metric_code === "revenue_receipts_total");
  const devolution = metrics.find((m) => m.metric_code === "devolution_from_centre_net");

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
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard
          title="Revenue Receipts"
          value={revReceipts?.value != null ? fmtCrore(revReceipts.value) : null}
          basis={revReceipts?.basis_tag}
          description={revReceipts?.fiscal_year ? `FY ${revReceipts.fiscal_year}` : undefined}
          lastUpdated={revReceipts ? now : null}
        />
        <MetricCard
          title="Devolution from Centre"
          value={devolution?.value != null ? fmtCrore(devolution.value) : null}
          basis={devolution?.basis_tag}
          description={devolution?.fiscal_year ? `FY ${devolution.fiscal_year}` : undefined}
          lastUpdated={devolution ? now : null}
        />
      </div>

      {chartData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-600">Receipts Over Time</h2>
          <TimeSeriesChart data={chartData} seriesKeys={["amount"]} yLabel="₹ Crore" />
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">AP vs Peers</h2>
        <p className="mb-4 text-xs text-slate-500">
          Own Tax Revenue (% of GSDP) compared with major states
        </p>
        <PeerCompareToggle
          metricCode="own_tax_revenue_pct_gsdp"
          label="Own Tax Revenue % GSDP"
          fiscalYear={revReceipts?.fiscal_year ?? "2023-24"}
          formatPreset="pct2"
        />
      </div>
    </div>
  );

  const dataContent = (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Receipt Records</h2>
          {basis && <BasisBadge basis={basis} size="md" className="mt-1" />}
        </div>
      </div>
      {basis && <TrustCopy basis={basis} />}
      <FilterBar
        fields={["financial_year", "basis", "period_type", "start_date", "end_date"]}
        defaults={filters}
      />
      {!result && <PageError retryHref="/receipts" />}
      {result && result.data.length === 0 && (
        <EmptyState variant={filters.financial_year || filters.basis ? "filtered" : "no-data"} />
      )}
      {result && result.data.length > 0 && (
        <>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="fiscal-receipts"
            csvHref={csvDownloadUrl("/fiscal/receipts", filters as Record<string, string | number | boolean | null | undefined>)}
            caption="Fiscal receipts"
          />
          <ProvenanceDrawer rows={result.data} label="Receipts Provenance" />
        </>
      )}
    </>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Receipts</h1>
          <p className="mt-1 text-slate-500">
            Revenue and capital receipts — with peer comparison
          </p>
          <LastUpdated timestamp={result ? now : null} className="mt-1" />
        </div>
      </div>
      <StoryDataLayout story={storyContent} data={dataContent} />
    </div>
  );
}
