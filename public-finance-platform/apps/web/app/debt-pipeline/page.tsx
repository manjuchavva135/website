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

export const metadata: Metadata = { title: "Debt Pipeline" };

type Props = { searchParams: Record<string, string | string[] | undefined> };

export default async function DebtPipelinePage({ searchParams }: Props) {
  const filters = parseCommonFilters(searchParams);
  const result = await api.debt.pipeline(filters);
  const now = new Date().toISOString();
  const basis = detectBasis(result?.data ?? []) ?? filters.basis ?? "scheduled";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Debt Pipeline</h1>
          <p className="mt-1 text-slate-500">
            Scheduled and notified borrowing events — not yet settled
          </p>
          <LastUpdated timestamp={result ? now : null} className="mt-1" />
        </div>
        <BasisBadge basis={basis} size="md" />
      </div>

      {/* Prominent scheduled trust copy */}
      <TrustCopy basis="scheduled" />

      <FilterBar
        fields={["financial_year", "basis", "start_date", "end_date"]}
        defaults={filters}
      />

      {!result && <PageError retryHref="/debt-pipeline" />}
      {result && result.data.length === 0 && (
        <EmptyState
          variant={filters.financial_year || filters.basis ? "filtered" : "no-data"}
          title="No pipeline events"
          message="No scheduled debt events match the current filters. Try removing date or basis constraints."
        />
      )}
      {result && result.data.length > 0 && (
        <>
          <div className="rounded-lg border border-slate-200 bg-amber-50/60 px-4 py-3 text-sm text-amber-800">
            <strong>{result.pagination.total}</strong> scheduled event
            {result.pagination.total !== 1 ? "s" : ""} in pipeline
          </div>
          <DataTable
            data={result.data}
            pagination={result.pagination}
            csvFilename="debt-pipeline"
            csvHref={csvDownloadUrl("/debt/pipeline", filters as Record<string, string | number | boolean | null | undefined>)}
            caption="Scheduled debt pipeline"
          />
          <ProvenanceDrawer rows={result.data} label="Pipeline Event Provenance" />
        </>
      )}
    </div>
  );
}
