import type { MetricObservation } from "@public-finance/shared-ts";
import { buildApiUrl } from "@/lib/api-url";

type Props = {
  observations: MetricObservation[];
};

export function SourceDrawer({ observations }: Props) {
  return (
    <details className="rounded-xl border border-slate-300 bg-white/80 p-4 shadow-sm">
      <summary className="cursor-pointer text-sm font-semibold uppercase tracking-wider text-slate-700">
        Source Drawer and Provenance
      </summary>
      <div className="mt-4 space-y-3 text-sm text-slate-700">
        {observations.length === 0 ? (
          <p>No observations available yet.</p>
        ) : (
          observations.slice(0, 8).map((item) => (
            <div key={item.id} className="rounded-lg border border-slate-200 p-3">
              <p className="font-medium text-slate-900">Observation #{item.id}</p>
              <p>Series: {item.series_slug}</p>
              <p>Basis: {item.basis}</p>
              <p>Source document id: {item.source_document_id}</p>
              <p>Source row id: {item.source_row_id ?? "n/a"}</p>
              <a
                href={buildApiUrl(`/api/v1/provenance/${item.id}`)}
                className="mt-2 inline-block text-tide underline"
                target="_blank"
                rel="noreferrer"
              >
                Open provenance JSON
              </a>
            </div>
          ))
        )}
      </div>
    </details>
  );
}
