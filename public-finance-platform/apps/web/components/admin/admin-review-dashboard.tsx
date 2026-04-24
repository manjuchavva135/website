"use client";

import Link from "next/link";
import React from "react";
import { useCallback, useEffect, useState } from "react";
import { adminApi, type ConflictComparison, type ReviewQueueItem } from "@/lib/admin-api";
import { useAdminAuth } from "./admin-auth";
import { AdminCard, AdminEmpty, AdminError, AdminSuccess, QueueStats, StatusPill } from "./admin-ui";

export function AdminReviewDashboard() {
  const { credentials } = useAdminAuth();
  const [documents, setDocuments] = useState<ReviewQueueItem[]>([]);
  const [conflicts, setConflicts] = useState<ConflictComparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [noteTarget, setNoteTarget] = useState("");
  const [note, setNote] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [documentPage, conflictRows] = await Promise.all([
        adminApi.documents(credentials, { new_only: true, page_size: 100 }),
        adminApi.conflicts(credentials),
      ]);
      setDocuments(documentPage.items);
      setConflicts(conflictRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load admin queue");
    } finally {
      setLoading(false);
    }
  }, [credentials]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveReconciliationNote(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingNote(true);
    setError(null);
    setSuccess(null);
    try {
      await adminApi.annotateReconciliation(credentials, Number(noteTarget), note);
      setNote("");
      setNoteTarget("");
      setSuccess("Reconciliation note saved to the audit trail.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save reconciliation note");
    } finally {
      setSavingNote(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-5" role="status" aria-label="Loading admin review queue">
        <div className="h-24 animate-pulse rounded-[2rem] bg-slate-200" />
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="h-96 animate-pulse rounded-[2rem] bg-slate-100" />
          <div className="h-96 animate-pulse rounded-[2rem] bg-slate-100" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.3em] text-teal-700">Review workflow</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950">Newly fetched documents</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Inspect parser output, resolve official-value conflicts, and move validated documents toward publication.
          </p>
        </div>
        <button
          className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          onClick={() => void load()}
        >
          Refresh
        </button>
      </div>

      {error && <AdminError message={error} />}
      {success && <AdminSuccess message={success} />}
      <QueueStats documents={documents} />

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <AdminCard title="Review queue" eyebrow="Documents">
          {documents.length === 0 ? (
            <AdminEmpty title="No new documents" message="There are no pending documents in the admin queue." />
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-200">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="p-3">Document</th>
                    <th className="p-3">Source</th>
                    <th className="p-3">Parser</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Open</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((item) => (
                    <tr key={item.document_id} className="border-t border-slate-100 align-top">
                      <td className="p-3">
                        <p className="font-semibold text-slate-900">{item.title}</p>
                        <p className="mt-1 font-mono text-xs text-slate-500">
                          {item.checksum_sha256.slice(0, 18)}...
                        </p>
                      </td>
                      <td className="p-3">{item.source_name}</td>
                      <td className="p-3">{item.parser_version ?? "n/a"}</td>
                      <td className="p-3">
                        <StatusPill status={item.review_status} />
                      </td>
                      <td className="p-3">
                        <Link
                          className="rounded-full bg-slate-950 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
                          href={`/admin/documents/${item.document_id}`}
                        >
                          Inspect
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </AdminCard>

        <AdminCard title="Conflicting official values" eyebrow="Reconciliation">
          {conflicts.length === 0 ? (
            <AdminEmpty
              title="No conflicts detected"
              message="The current official-source comparisons do not contain differing values."
            />
          ) : (
            <div className="space-y-3">
              {conflicts.map((conflict) => (
                <article
                  key={`${conflict.entity}-${conflict.metric_code ?? conflict.as_of_date}-${conflict.left_source}-${conflict.right_source}`}
                  className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">
                        {conflict.metric_code ?? conflict.as_of_date ?? conflict.entity}
                      </p>
                      <p className="text-xs text-slate-600">{conflict.entity} / {conflict.basis_tag}</p>
                    </div>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-amber-800">
                      Delta {conflict.difference}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-xl bg-white p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-400">{conflict.left_source}</p>
                      <p className="mt-1 font-mono font-semibold">{conflict.left_value}</p>
                    </div>
                    <div className="rounded-xl bg-white p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-400">{conflict.right_source}</p>
                      <p className="mt-1 font-mono font-semibold">{conflict.right_value}</p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </AdminCard>
      </div>

      <AdminCard title="Reconciliation note" eyebrow="Annotation">
        <form className="grid gap-3 lg:grid-cols-[220px_1fr_auto]" onSubmit={saveReconciliationNote}>
          <input
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
            inputMode="numeric"
            min="1"
            placeholder="Result ID"
            required
            type="number"
            value={noteTarget}
            onChange={(event) => setNoteTarget(event.target.value)}
          />
          <input
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
            placeholder="Explain authoritative source or reconciliation decision"
            required
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          <button
            className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
            disabled={savingNote}
          >
            {savingNote ? "Saving..." : "Save note"}
          </button>
        </form>
      </AdminCard>
    </div>
  );
}
