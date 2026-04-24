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

export const metadata: Metadata = { title: "Debt Overview" };

type Props = { searchParams: Record<string, string | string[] | undefined> };

export default async function DebtOverviewPage({ searchParams }: Props) {
  const filters = parseCommonFilters(searchParams);
  const result = await api.debt.outstanding(filters);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Debt Overview</h1>
          <p className="mt-1 text-slate-500">Outstanding principal stock with instrument-level provenance</p>
          <LastUpdated timestamp={result ? now : null} className="mt-1" />
        </div>
        {basis && <BasisBadge basis={basis} size="md" />}
      </div>

      {basis && <TrustCopy basis={basis} />}

      {/* Filters */}
      <FilterBar
        fields={["financial_year", "basis", "as_of", "start_date", "end_date"]}
        defaults={filters}
      />

      {/* Summary cards */}
      {result && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard
            title="Total Records"
            value={result.pagination.total}
            description="Debt position records matching filters"
            basis={basis}
            lastUpdated={now}
          />
          <MetricCard
            title="Current Page"
            value={`${result.pagination.page} / ${Math.ceil(result.pagination.total / result.pagination.page_size)}`}
            description="Page navigation"
            lastUpdated={now}
          />
          <MetricCard
            title="Page Size"
            value={result.pagination.page_size}
            description="Records per page"
            lastUpdated={now}
          />
        </div>
      )}

      {/* Data */}
      {!result && <PageError retryHref="/debt-overview" />}
      {result && result.data.length === 0 && (
        <EmptyState variant={filters.financial_year || filters.basis ? "filtered" : "no-data"} />
      )}
      {result && result.data.length > 0 && (
        <>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="debt-outstanding"
            csvHref={csvDownloadUrl("/debt/outstanding", filters as Record<string, string | number | boolean | null | undefined>)}
            caption="Outstanding debt stock"
          />
          <ProvenanceDrawer rows={result.data} label="Debt Position Provenance" />
        </>
      )}
    </div>
  );
}
