import { buildApiUrl } from "@/lib/api-url";

interface ProvenanceItem {
  document_id?: number;
  source_document_id?: number;
  page?: number | null;
  row?: number | null;
  source_row_id?: number | null;
  basis?: string;
  basis_tag?: string;
  provenance_note?: string | null;
}

interface ProvenanceDrawerProps {
  rows: Record<string, unknown>[];
  label?: string;
}

function extractProvenance(rows: Record<string, unknown>[]): ProvenanceItem[] {
  const seen = new Set<number>();
  const items: ProvenanceItem[] = [];

  for (const row of rows) {
    // Embedded _provenance arrays from embed_provenance()
    const embedded = row["_provenance"];
    if (Array.isArray(embedded)) {
      for (const p of embedded as ProvenanceItem[]) {
        const id = p.document_id ?? p.source_document_id;
        if (id !== undefined && !seen.has(id)) {
          seen.add(id);
          items.push(p);
        }
      }
    } else {
      // Flat provenance fields on the row itself
      const id = row["source_document_id"];
      if (typeof id === "number" && !seen.has(id)) {
        seen.add(id);
        items.push({
          source_document_id: id,
          source_row_id:
            typeof row["source_row_id"] === "number" ? row["source_row_id"] : null,
          basis: typeof row["basis_tag"] === "string" ? row["basis_tag"] : undefined,
          provenance_note:
            typeof row["provenance_note"] === "string" ? row["provenance_note"] : null,
        });
      }
    }
  }
  return items;
}

export function ProvenanceDrawer({ rows, label = "Source Provenance" }: ProvenanceDrawerProps) {
  const items = extractProvenance(rows);

  return (
    <details className="rounded-xl border border-slate-200 bg-white/80 shadow-sm backdrop-blur">
      <summary className="flex cursor-pointer items-center gap-2 px-5 py-4 text-sm font-semibold uppercase tracking-wider text-slate-600 marker:hidden">
        <span
          className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-xs text-slate-500"
          aria-hidden="true"
        >
          ⊙
        </span>
        {label}
        <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-500">
          {items.length} source{items.length !== 1 ? "s" : ""}
        </span>
      </summary>

      <div className="border-t border-slate-100 px-5 pb-5 pt-4">
        {items.length === 0 ? (
          <p className="text-sm text-slate-400">
            No provenance metadata embedded in this dataset. Raw data may lack row-level linking.
          </p>
        ) : (
          <ul className="space-y-3">
            {items.map((item, i) => {
              const docId = item.document_id ?? item.source_document_id;
              const basis = item.basis ?? item.basis_tag;
              return (
                <li
                  key={i}
                  className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3 text-sm"
                >
                  <div className="flex flex-wrap items-start gap-x-4 gap-y-1">
                    {docId !== undefined && (
                      <span>
                        <span className="font-medium text-slate-600">Doc ID:</span>{" "}
                        <a
                          href={buildApiUrl(`/api/v1/provenance/${docId}`)}
                          target="_blank"
                          rel="noreferrer"
                          className="text-tide underline hover:text-teal-700"
                        >
                          {docId}
                        </a>
                      </span>
                    )}
                    {item.source_row_id !== null && item.source_row_id !== undefined && (
                      <span>
                        <span className="font-medium text-slate-600">Row:</span>{" "}
                        {item.source_row_id}
                      </span>
                    )}
                    {item.page !== null && item.page !== undefined && (
                      <span>
                        <span className="font-medium text-slate-600">Page:</span> {item.page}
                      </span>
                    )}
                    {basis && (
                      <span>
                        <span className="font-medium text-slate-600">Basis:</span> {basis}
                      </span>
                    )}
                  </div>
                  {item.provenance_note && (
                    <p className="mt-1.5 text-slate-500">{item.provenance_note}</p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </details>
  );
}
