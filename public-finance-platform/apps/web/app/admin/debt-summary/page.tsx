"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { adminApi, type DebtSummaryResponse } from "@/lib/admin-api";
import { useAdminAuth } from "@/components/admin/admin-auth";
import { AdminCard, AdminError } from "@/components/admin/admin-ui";

export default function AdminDebtSummaryPage() {
  const { credentials } = useAdminAuth();
  const [summary, setSummary] = useState<DebtSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setSummary(await adminApi.debtSummary(credentials));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load debt summary");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [credentials]);

  const total = summary?.total_outstanding_inr_crore ?? "0";
  const buckets =
    summary?.buckets?.map((b) => ({
      label: b.label,
      amount: Number(b.amount),
    })) ?? [];

  return (
    <AdminCard eyebrow="Debt" title="AP outstanding SDL debt">
      {error && <AdminError message={error} />}

      <div className="mb-6 flex flex-wrap items-baseline gap-6">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Total outstanding
          </div>
          <div className="mt-1 text-3xl font-bold text-slate-900">
            ₹ {Number(total).toLocaleString("en-IN", { maximumFractionDigits: 2 })} cr
          </div>
        </div>
        <div className="grid grid-cols-2 gap-x-8 text-sm text-slate-600">
          <span>Authoritative positions</span>
          <span className="font-semibold text-slate-900">
            {summary?.instruments_authoritative ?? "—"}
          </span>
          <span>Computed-from-events</span>
          <span className="font-semibold text-slate-900">
            {summary?.instruments_computed ?? "—"}
          </span>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="ml-auto rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="mb-8 h-72 w-full">
        {buckets.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={buckets} margin={{ top: 16, right: 24, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#475569" }} />
              <YAxis
                tick={{ fontSize: 12, fill: "#475569" }}
                tickFormatter={(v: number) => v.toLocaleString("en-IN")}
              />
              <Tooltip
                formatter={(v: number) => `₹ ${v.toLocaleString("en-IN")} cr`}
                cursor={{ fill: "rgba(15, 23, 42, 0.04)" }}
              />
              <Bar dataKey="amount" fill="#0f766e" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-300 text-sm text-slate-500">
            No debt positions to chart yet.
          </div>
        )}
      </div>

      {summary?.last_reconciliation?.id && (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Last reconciliation
          </div>
          <div className="mt-1 text-slate-700">
            <code className="rounded bg-white px-1.5 py-0.5">
              {summary.last_reconciliation.name ?? "—"}
            </code>{" "}
            · status {summary.last_reconciliation.status} ·{" "}
            {summary.last_reconciliation.completed_at
              ? `completed ${new Date(summary.last_reconciliation.completed_at).toLocaleString()}`
              : "in progress"}
          </div>
          {summary.last_reconciliation.scope_json && (
            <pre className="mt-2 overflow-x-auto rounded-xl bg-white p-3 text-xs text-slate-700">
              {summary.last_reconciliation.scope_json}
            </pre>
          )}
        </div>
      )}
    </AdminCard>
  );
}
