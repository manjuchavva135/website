import type { Metadata } from "next";
import { api, csvDownloadUrl } from "@/lib/api";
import { parseCommonFilters } from "@/lib/query-params";
import { FilterBar } from "@/components/data/filter-bar";
import { DataTable } from "@/components/data/data-table";
import { LastUpdated } from "@/components/ui/last-updated";
import { EmptyState } from "@/components/ui/empty-state";
import { PageError } from "@/components/ui/page-error";
import { MetricCard } from "@/components/ui/metric-card";
import { ProvenanceDrawer } from "@/components/provenance-drawer";

export const metadata: Metadata = { title: "Source Documents" };

type Props = { searchParams: Record<string, string | string[] | undefined> };

export default async function SourcesPage({ searchParams }: Props) {
  const filters = parseCommonFilters(searchParams);
  const result = await api.sources({
    financial_year: filters.financial_year,
    start_date: filters.start_date,
    end_date: filters.end_date,
    page: filters.page,
    page_size: filters.page_size,
  });
  const now = new Date().toISOString();
  const hasActiveFilters = Boolean(filters.financial_year || filters.start_date || filters.end_date);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Source Documents</h1>
          <p className="mt-1 text-slate-500">
            All source artifacts ingested — RBI, AP Finance Department, and CAG publications
          </p>
          <LastUpdated timestamp={result ? now : null} className="mt-1" />
        </div>
      </div>

      {/* Context */}
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        Every metric published on this platform is traceable to a specific source document, page,
        and row. The table below lists all ingested artifacts with their parser version and checksum.
      </div>

      <FilterBar
        fields={["financial_year", "start_date", "end_date"]}
        defaults={filters}
      />

      {result && (
        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard
            title="Total Sources"
            value={result.pagination.total}
            description="Source documents in catalog"
            lastUpdated={now}
          />
        </div>
      )}

      {!result && <PageError retryHref="/sources" />}
      {result && result.data.length === 0 && (
        <EmptyState
          variant={hasActiveFilters ? "filtered" : "under-review"}
          title={hasActiveFilters ? "No source documents for these filters" : "Source documents under review"}
          message={
            hasActiveFilters
              ? "No source documents match the selected period. Try broadening the filter range."
              : "Source documents are in the review queue and will appear here once approved."
          }
          action={{ label: "Go to Admin", href: "/admin/review-queue" }}
        />
      )}
      {result && result.data.length > 0 && (
        <>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="source-catalog"
            csvHref={csvDownloadUrl("/sources", {
              financial_year: filters.financial_year,
              start_date: filters.start_date,
              end_date: filters.end_date,
            })}
            caption="Source document catalog"
          />
          <ProvenanceDrawer rows={result.data} label="Source Catalog Provenance" />
        </>
      )}
    </div>
  );
}
