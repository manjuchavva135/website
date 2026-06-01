"use client";

import { useState, useCallback } from "react";
import { buildApiUrl } from "@/lib/api-url";
import type {
  PeerMetricCatalogEntry,
  PeerSnapshotResponse,
  PeerSeriesResponse,
} from "@/lib/api";
import { BarChartClient, type BarDataPoint } from "@/components/charts/bar-chart-client";
import { MultiSeriesLineChart, type MultiSeriesPoint } from "@/components/charts/multi-series-line-chart";

const DEFAULT_STATES = ["AP", "TN", "KA", "MH", "TS", "RJ", "UP"];

const GROUP_LABELS: Record<string, string> = {
  deficit_fiscal: "Fiscal Deficit",
  deficit_revenue: "Revenue Deficit",
  debt_outstanding: "Debt",
  debt_issued: "Debt Issuance",
  debt_pipeline: "Debt Pipeline",
  receipts_tax: "Tax Revenue",
  receipts_non_tax: "Non-Tax Revenue",
  receipts_grants: "Transfers & Grants",
  expenditure_revenue: "Revenue Expenditure",
  expenditure_capital: "Capital / Social Sector",
};

interface Props {
  metrics: PeerMetricCatalogEntry[];
}

type ViewMode = "snapshot" | "series";

export function PeerCompareExplorer({ metrics }: Props) {
  const [selected, setSelected] = useState<PeerMetricCatalogEntry | null>(null);
  const [fiscalYear, setFiscalYear] = useState("2023-24");
  const [viewMode, setViewMode] = useState<ViewMode>("snapshot");
  const [snapshotData, setSnapshotData] = useState<BarDataPoint[] | null>(null);
  const [seriesData, setSeriesData] = useState<{ data: MultiSeriesPoint[]; keys: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSnapshot = useCallback(
    async (metricCode: string, fy: string) => {
      setLoading(true);
      setError(null);
      setSnapshotData(null);
      try {
        const url = buildApiUrl(`/api/v1/peer-comparison/${encodeURIComponent(metricCode)}`, {
          states: DEFAULT_STATES.join(","),
          fiscal_year: fy,
        });
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as PeerSnapshotResponse;
        const m = metrics.find((x) => x.metric_code === metricCode);
        const label = m?.metric_name ?? metricCode;
        const chartData: BarDataPoint[] = json.data
          .filter((row) => row.value != null)
          .map((row) => ({ label: row.state_code, [label]: row.value as number }));
        setSnapshotData(chartData);
      } catch {
        setError("Could not load peer data");
      } finally {
        setLoading(false);
      }
    },
    [metrics]
  );

  const fetchSeries = useCallback(async (metricCode: string) => {
    setLoading(true);
    setError(null);
    setSeriesData(null);
    try {
      const url = buildApiUrl(`/api/v1/peer-comparison/${encodeURIComponent(metricCode)}`, {
        states: DEFAULT_STATES.join(","),
      });
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as PeerSeriesResponse;
      const allYears = Array.from(
        new Set(Object.values(json.series).flatMap((pts) => pts.map((p) => p.fiscal_year)))
      ).sort();
      const pivoted: MultiSeriesPoint[] = allYears.map((fy) => {
        const row: MultiSeriesPoint = { label: fy };
        for (const [stateCode, pts] of Object.entries(json.series)) {
          const pt = pts.find((p) => p.fiscal_year === fy);
          row[stateCode] = pt?.value ?? null;
        }
        return row;
      });
      setSeriesData({ data: pivoted, keys: Object.keys(json.series) });
    } catch {
      setError("Could not load peer data");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSelect = (m: PeerMetricCatalogEntry) => {
    setSelected(m);
    setViewMode("snapshot");
    void fetchSnapshot(m.metric_code, fiscalYear);
  };

  const handleViewMode = (mode: ViewMode) => {
    setViewMode(mode);
    if (!selected) return;
    if (mode === "series" && !seriesData) {
      void fetchSeries(selected.metric_code);
    }
    if (mode === "snapshot" && !snapshotData) {
      void fetchSnapshot(selected.metric_code, fiscalYear);
    }
  };

  const handleYearChange = (fy: string) => {
    setFiscalYear(fy);
    if (selected) {
      void fetchSnapshot(selected.metric_code, fy);
    }
  };

  // Group metrics
  const groups = metrics.reduce<Record<string, PeerMetricCatalogEntry[]>>((acc, m) => {
    const g = m.metric_group;
    if (!acc[g]) acc[g] = [];
    acc[g].push(m);
    return acc;
  }, {});

  const dataKey = selected?.metric_name ?? "";

  return (
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      {/* ── Metric selector ────────────────────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
        <p className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400">
          Select Metric
        </p>
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1">
          {Object.entries(groups).map(([group, items]) => (
            <div key={group}>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                {GROUP_LABELS[group] ?? group}
              </p>
              {items.map((m) => (
                <button
                  key={m.metric_code}
                  onClick={() => handleSelect(m)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                    selected?.metric_code === m.metric_code
                      ? "bg-tide/10 text-tide font-medium"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-800"
                  }`}
                >
                  {m.metric_name}
                  <span className="ml-1 text-slate-400">
                    ({m.state_count} states)
                  </span>
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* ── Chart panel ────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        {!selected && (
          <div className="flex h-64 items-center justify-center text-slate-400 text-sm">
            Select a metric from the left panel to compare states
          </div>
        )}

        {selected && (
          <>
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-slate-800">{selected.metric_name}</h2>
                <p className="text-xs text-slate-500">
                  {GROUP_LABELS[selected.metric_group] ?? selected.metric_group} ·{" "}
                  {selected.unit_scale} · {selected.state_count} states
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {viewMode === "snapshot" && (
                  <select
                    value={fiscalYear}
                    onChange={(e) => handleYearChange(e.target.value)}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 focus:border-tide focus:outline-none"
                  >
                    {["2024-25", "2023-24", "2022-23", "2021-22", "2020-21", "2019-20"].map((fy) => (
                      <option key={fy} value={fy}>{fy}</option>
                    ))}
                  </select>
                )}
                <div className="flex rounded-lg border border-slate-200 bg-white text-xs overflow-hidden">
                  <button
                    onClick={() => handleViewMode("snapshot")}
                    className={`px-3 py-1.5 ${viewMode === "snapshot" ? "bg-tide/10 text-tide font-medium" : "text-slate-500 hover:bg-slate-50"}`}
                  >
                    Snapshot
                  </button>
                  <button
                    onClick={() => handleViewMode("series")}
                    className={`border-l border-slate-200 px-3 py-1.5 ${viewMode === "series" ? "bg-tide/10 text-tide font-medium" : "text-slate-500 hover:bg-slate-50"}`}
                  >
                    Trend
                  </button>
                </div>
              </div>
            </div>

            {loading && (
              <div className="flex h-64 items-center justify-center text-sm text-slate-400">
                Loading…
              </div>
            )}
            {error && !loading && (
              <div className="flex h-64 items-center justify-center text-sm text-red-400">
                {error}
              </div>
            )}
            {!loading && !error && viewMode === "snapshot" && snapshotData && (
              <BarChartClient
                data={snapshotData}
                dataKey={dataKey}
                color="#0ea5a4"
                height={320}
              />
            )}
            {!loading && !error && viewMode === "series" && seriesData && (
              <MultiSeriesLineChart
                data={seriesData.data}
                seriesKeys={seriesData.keys}
                height={320}
              />
            )}
            <p className="mt-3 text-[10px] text-slate-400">
              States: {DEFAULT_STATES.join(", ")} · Source: RBI State Finances Accounts
            </p>
          </>
        )}
      </div>
    </div>
  );
}
