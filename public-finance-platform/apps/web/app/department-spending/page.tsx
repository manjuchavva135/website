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

export const metadata: Metadata = { title: "Department Spending" };

type Props = { searchParams: Record<string, string | string[] | undefined> };

export default async function DepartmentSpendingPage({ searchParams }: Props) {
  const filters = parseCommonFilters(searchParams);
  const result = await api.departments.spending(filters);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis;

  // Build chart: top 10 departments by actual expenditure
  const deptMap = new Map<string, number>();
  for (const row of result?.data ?? []) {
    const dept = String(row["department_name"] ?? row["department"] ?? "Unknown");
    const amt = Number(row["actual_expenditure"] ?? row["amount"] ?? 0);
    deptMap.set(dept, (deptMap.get(dept) ?? 0) + amt);
  }
  const chartData = [...deptMap.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([label, amount]) => ({ label, amount }));

  // Unique departments for filter dropdown
  const departments = [...new Set((result?.data ?? []).map((r) => String(r["department_name"] ?? r["department"] ?? "")))].filter(Boolean).slice(0, 50);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Department Spending</h1>
          <p className="mt-1 text-slate-500">Sanctioned vs actual expenditure by department</p>
          <LastUpdated timestamp={result ? now : null} className="mt-1" />
        </div>
        {basis && <BasisBadge basis={basis} size="md" />}
      </div>

      {basis && <TrustCopy basis={basis} />}

      <FilterBar
        fields={["financial_year", "basis", "department", "start_date", "end_date"]}
        defaults={filters}
        departments={departments}
      />

      {result && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard
            title="Departments"
            value={departments.length}
            description="Unique departments in current results"
            basis={basis}
            lastUpdated={now}
          />
          <MetricCard
            title="Total Records"
            value={result.pagination.total}
            description="Spending records matching filters"
            lastUpdated={now}
          />
        </div>
      )}

      {result && result.data.length > 0 && chartData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-600">Top Departments by Expenditure</h2>
          <BarChartClient
            data={chartData}
            dataKey="amount"
            horizontal
            height={Math.max(300, chartData.length * 40)}
          />
        </div>
      )}

      {!result && <PageError retryHref="/department-spending" />}
      {result && result.data.length === 0 && (
        <EmptyState variant={filters.financial_year || filters.basis ? "filtered" : "no-data"} />
      )}
      {result && result.data.length > 0 && (
        <>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="department-spending"
            csvHref={csvDownloadUrl("/departments/spending", filters as Record<string, string | number | boolean | null | undefined>)}
            caption="Department-wise spending"
          />
          <ProvenanceDrawer rows={result.data} label="Department Spending Provenance" />
        </>
      )}
    </div>
  );
}
