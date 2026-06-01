"use client";

import { useState, useCallback } from "react";
import { buildApiUrl } from "@/lib/api-url";
import type { PeerSnapshotResponse, PeerSeriesResponse } from "@/lib/api";
import { BarChartClient, type BarDataPoint } from "@/components/charts/bar-chart-client";
import { MultiSeriesLineChart, type MultiSeriesPoint } from "@/components/charts/multi-series-line-chart";

// Default peer states for comparison
const DEFAULT_STATES = ["AP", "TN", "KA", "MH", "TS", "RJ", "UP"];

type FormatPreset = "pct1" | "pct2" | "inr_crore" | "number";

function resolveFormatter(preset?: FormatPreset): (v: number) => string {
  switch (preset) {
    case "pct2": return (v) => v.toFixed(2) + "%";
    case "inr_crore": return (v) => "\u20b9 " + v.toLocaleString("en-IN") + " cr";
    case "number": return (v) => v.toLocaleString("en-IN");
    case "pct1":
    default: return (v) => v.toFixed(1) + "%";
  }
}

interface PeerCompareToggleProps {
  metricCode: string;
  label: string;
  fiscalYear: string;
  /** Override the default comparison states */
  states?: string[];
  /** Preset formatter for chart values (must be serializable from Server Components) */
  formatPreset?: FormatPreset;
}

type ViewMode = "snapshot" | "series";

export function PeerCompareToggle({
  metricCode,
  label,
  fiscalYear,
  states = DEFAULT_STATES,
  formatPreset,
}: PeerCompareToggleProps) {
  const formatter = resolveFormatter(formatPreset);
  const [open, setOpen] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("snapshot");
  const [snapshotData, setSnapshotData] = useState<BarDataPoint[] | null>(null);
  const [seriesData, setSeriesData] = useState<{ data: MultiSeriesPoint[]; keys: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSnapshot = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = buildApiUrl(`/api/v1/peer-comparison/${encodeURIComponent(metricCode)}`, {
        states: states.join(","),
        fiscal_year: fiscalYear,
      });
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as PeerSnapshotResponse;
      const chartData: BarDataPoint[] = json.data
        .filter((row) => row.value != null)
        .map((row) => ({ label: row.state_code, [label]: row.value as number }));
      setSnapshotData(chartData);
    } catch {
      setError("Could not load peer data");
    } finally {
      setLoading(false);
    }
  }, [metricCode, states, fiscalYear, label]);

  const fetchSeries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = buildApiUrl(`/api/v1/peer-comparison/${encodeURIComponent(metricCode)}`, {
        states: states.join(","),
      });
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as PeerSeriesResponse;
      // Pivot: rows are fiscal_years, columns are state_codes
      const allYears = Array.from(
        new Set(
          Object.values(json.series).flatMap((pts) => pts.map((p) => p.fiscal_year))
        )
      ).sort();
      const pivoted: MultiSeriesPoint[] = allYears.map((fy) => {
        const row: MultiSeriesPoint = { label: fy };
        for (const [stateCode, pts] of Object.entries(json.series)) {
          const pt = pts.find((p) => p.fiscal_year === fy);
          row[stateCode] = pt?.value ?? null;
        }
        return row;
      });
      const seriesKeys = Object.keys(json.series);
      setSeriesData({ data: pivoted, keys: seriesKeys });
    } catch {
      setError("Could not load peer data");
    } finally {
      setLoading(false);
    }
  }, [metricCode, states]);

  const handleToggle = () => {
    const nextOpen = !open;
    setOpen(nextOpen);
    if (nextOpen && snapshotData === null) {
      void fetchSnapshot();
    }
  };

  const handleViewMode = (mode: ViewMode) => {
    setViewMode(mode);
    if (mode === "series" && seriesData === null) {
      void fetchSeries();
    }
    if (mode === "snapshot" && snapshotData === null) {
      void fetchSnapshot();
    }
  };

  return (
    <div>
      <button
        onClick={handleToggle}
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
          open
            ? "border-tide/30 bg-tide/10 text-tide"
            : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-700"
        }`}
      >
        <span className={`inline-block h-2 w-2 rounded-full ${open ? "bg-tide" : "bg-slate-300"}`} />
        Compare with peers
      </button>

      {open && (
        <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50/60 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="text-xs font-semibold text-slate-600">
              {label} — AP vs peers
              {viewMode === "snapshot" && ` (${fiscalYear})`}
            </p>
            <div className="flex rounded-lg border border-slate-200 bg-white text-xs overflow-hidden">
              <button
                onClick={() => handleViewMode("snapshot")}
                className={`px-3 py-1 ${viewMode === "snapshot" ? "bg-tide/10 text-tide font-medium" : "text-slate-500 hover:bg-slate-50"}`}
              >
                Snapshot
              </button>
              <button
                onClick={() => handleViewMode("series")}
                className={`border-l border-slate-200 px-3 py-1 ${viewMode === "series" ? "bg-tide/10 text-tide font-medium" : "text-slate-500 hover:bg-slate-50"}`}
              >
                Trend
              </button>
            </div>
          </div>

          {loading && (
            <div className="flex h-40 items-center justify-center text-sm text-slate-400">
              Loading…
            </div>
          )}

          {error && !loading && (
            <div className="flex h-40 items-center justify-center text-sm text-red-400">
              {error}
            </div>
          )}

          {!loading && !error && viewMode === "snapshot" && snapshotData && (
            <BarChartClient
              data={snapshotData}
              dataKey={label}
              color="#0ea5a4"
              height={240}
            />
          )}

          {!loading && !error && viewMode === "series" && seriesData && (
            <MultiSeriesLineChart
              data={seriesData.data}
              seriesKeys={seriesData.keys}
              height={240}
              formatter={formatter as (v: number) => string}
            />
          )}

          <p className="mt-2 text-[10px] text-slate-400">
            States shown: {states.join(", ")} · Source: RBI State Finances
          </p>
        </div>
      )}
    </div>
  );
}
