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

export const metadata: Metadata = { title: "Repayments" };

type Props = { searchParams: Record<string, string | string[] | undefined> };

export default async function RepaymentsPage({ searchParams }: Props) {
  const filters = parseCommonFilters(searchParams);
  const result = await api.debt.repayments(filters);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis;

  // Build time-series chart data
  const chartData: TimeSeriesPoint[] = Object.values(
    (result?.data ?? []).reduce<Record<string, TimeSeriesPoint>>((acc, row) => {
      const label =
        (row["period_label"] as string) ??
        (row["event_date"] as string)?.slice(0, 7) ??
        "Unknown";
      if (!acc[label]) acc[label] = { label, principal: 0, coupon: 0 };
      const t = String(row["event_type"] ?? "");
      const amt = Number(row["amount"] ?? 0);
      if (t.includes("principal")) (acc[label] as Record<string, number>)["principal"] += amt;
      if (t.includes("coupon")) (acc[label] as Record<string, number>)["coupon"] += amt;
      return acc;
    }, {})
  ).slice(0, 24);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Debt Repayments</h1>
          <p className="mt-1 text-slate-500">Principal and coupon repayments — due and settled</p>
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
            description="Repayment events matching filters"
            basis={basis}
            lastUpdated={now}
          />
        </div>
      )}

      {/* Chart */}
      {result && result.data.length > 0 && chartData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-600">
            Repayments over Time (Principal vs Coupon)
          </h2>
          <TimeSeriesChart
            data={chartData}
            seriesKeys={["principal", "coupon"]}
            yLabel="Amount"
          />
        </div>
      )}

      {!result && <PageError retryHref="/repayments" />}
      {result && result.data.length === 0 && (
        <EmptyState variant={filters.financial_year || filters.basis ? "filtered" : "no-data"} />
      )}
      {result && result.data.length > 0 && (
        <>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="debt-repayments"
            csvHref={csvDownloadUrl("/debt/repayments", filters as Record<string, string | number | boolean | null | undefined>)}
            caption="Debt repayment schedule"
          />
          <ProvenanceDrawer rows={result.data} label="Repayment Provenance" />
        </>
      )}
    </div>
  );
}
