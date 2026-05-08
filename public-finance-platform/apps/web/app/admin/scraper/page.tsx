"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, type ScraperStatusResponse } from "@/lib/admin-api";
import { useAdminAuth } from "@/components/admin/admin-auth";
import { AdminCard, AdminError } from "@/components/admin/admin-ui";

type Banner =
  | { kind: "idle" }
  | { kind: "ok"; message: string }
  | { kind: "error"; message: string };

export default function AdminScraperPage() {
  const { credentials } = useAdminAuth();
  const [status, setStatus] = useState<ScraperStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<Banner>({ kind: "idle" });
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.scraperStatus(credentials);
      setStatus(data);
    } catch (err) {
      setBanner({
        kind: "error",
        message: err instanceof Error ? err.message : "Failed to load scraper status",
      });
    } finally {
      setLoading(false);
    }
  }, [credentials]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function trigger() {
    setBusy(true);
    setBanner({ kind: "idle" });
    try {
      await adminApi.triggerScraper(credentials);
      setBanner({ kind: "ok", message: "Scraper task queued. Check back shortly." });
      await refresh();
    } catch (err) {
      setBanner({
        kind: "error",
        message: err instanceof Error ? err.message : "Trigger failed",
      });
    } finally {
      setBusy(false);
    }
  }

  const last = status?.runs?.[0];

  return (
    <AdminCard eyebrow="Ingestion" title="RBI press-release scraper">
      <p className="mb-4 text-sm text-slate-600">
        Scrapes the RBI press release page for new "Auction of State Government
        Securities" PDFs and ingests any rows for Andhra Pradesh. Runs Tue/Fri
        at 03:00 UTC; trigger manually below.
      </p>

      {banner.kind === "ok" && (
        <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {banner.message}
        </div>
      )}
      {banner.kind === "error" && <AdminError message={banner.message} />}

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <button
          type="button"
          disabled={busy}
          onClick={trigger}
          className="rounded-xl bg-slate-950 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
        >
          {busy ? "Queuing…" : "Run scraper now"}
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={() => void refresh()}
          className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
        <div className="text-xs text-slate-500">
          Task: <code className="rounded bg-slate-100 px-1 py-0.5">{status?.task_name ?? "—"}</code>
        </div>
      </div>

      <div className="mb-3 text-sm font-semibold text-slate-700">
        Last run: {last ? <StatusBadge status={last.status} /> : <span className="text-slate-400">none</span>}
        {last?.started_at && (
          <span className="ml-2 font-normal text-slate-500">
            started {new Date(last.started_at).toLocaleString()}
          </span>
        )}
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">#</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Started</th>
              <th className="px-4 py-2">Completed</th>
              <th className="px-4 py-2">Detail</th>
            </tr>
          </thead>
          <tbody>
            {(status?.runs ?? []).map((run) => (
              <tr key={run.id} className="border-t border-slate-100 align-top">
                <td className="px-4 py-2 text-slate-500">{run.id}</td>
                <td className="px-4 py-2"><StatusBadge status={run.status} /></td>
                <td className="px-4 py-2 text-slate-600">
                  {run.started_at ? new Date(run.started_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-2 text-slate-600">
                  {run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-2 text-xs text-slate-500">
                  {run.error_message
                    ? <span className="text-rose-700">{run.error_message}</span>
                    : run.response_headers_json ?? "—"}
                </td>
              </tr>
            ))}
            {(status?.runs ?? []).length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">
                  No scraper runs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </AdminCard>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls = status.includes("succ")
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : status.includes("fail")
    ? "bg-rose-50 text-rose-700 border-rose-200"
    : "bg-slate-50 text-slate-700 border-slate-200";
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {status}
    </span>
  );
}
