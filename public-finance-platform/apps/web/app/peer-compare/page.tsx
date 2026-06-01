import type { Metadata } from "next";
import { api } from "@/lib/api";
import { LastUpdated } from "@/components/ui/last-updated";
import { PageError } from "@/components/ui/page-error";
import { PeerCompareExplorer } from "./peer-compare-explorer";

export const metadata: Metadata = { title: "Peer Comparison — AP vs States" };

export default async function PeerComparePage() {
  const catalog = await api.peers.metricCatalog();
  const now = new Date().toISOString();

  if (!catalog) return <PageError retryHref="/peer-compare" />;

  // Group metrics by group
  const groups = catalog.metrics.reduce<Record<string, typeof catalog.metrics>>(
    (acc, m) => {
      const g = m.metric_group;
      if (!acc[g]) acc[g] = [];
      acc[g].push(m);
      return acc;
    },
    {}
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Peer Comparison</h1>
          <p className="mt-1 text-slate-500">
            Compare Andhra Pradesh with major states across fiscal, debt, and expenditure metrics
          </p>
          <LastUpdated timestamp={now} className="mt-1" />
        </div>
        <span className="inline-flex items-center rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700 ring-1 ring-inset ring-teal-200">
          Source: RBI State Finances
        </span>
      </div>

      <div className="rounded-xl bg-slate-50 border border-slate-200 px-5 py-3 text-sm text-slate-600">
        <span className="font-medium">
          {catalog.metrics.length} metrics available
        </span>{" "}
        across {Object.keys(groups).length} categories — select any metric to compare AP with
        selected peer states over time or as a snapshot.
      </div>

      <PeerCompareExplorer metrics={catalog.metrics} />
    </div>
  );
}
