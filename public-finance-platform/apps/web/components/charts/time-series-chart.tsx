"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export interface TimeSeriesPoint {
  label: string;
  [key: string]: string | number;
}

interface TimeSeriesChartProps {
  data: TimeSeriesPoint[];
  /** Keys in each data object to plot as lines (exclude "label") */
  seriesKeys: string[];
  colors?: string[];
  yLabel?: string;
  height?: number;
}

const DEFAULT_COLORS = [
  "#0ea5a4", // tide
  "#6366f1", // indigo
  "#f59e0b", // amber
  "#10b981", // emerald
  "#f43f5e", // rose
];

export function TimeSeriesChart({
  data,
  seriesKeys,
  colors = DEFAULT_COLORS,
  yLabel,
  height = 300,
}: TimeSeriesChartProps) {
  if (data.length === 0) {
    return (
      <div
        className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-400"
        role="img"
        aria-label="No chart data available"
      >
        No data to display
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 12, fill: "#64748b" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "#64748b" }}
            tickLine={false}
            axisLine={false}
            label={
              yLabel
                ? { value: yLabel, angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#94a3b8" } }
                : undefined
            }
            tickFormatter={(v) =>
              typeof v === "number"
                ? new Intl.NumberFormat("en-IN", { notation: "compact", compactDisplay: "short" }).format(v)
                : v
            }
          />
          <Tooltip
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) =>
              typeof value === "number"
                ? new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(value)
                : String(value ?? "")
            }
            labelStyle={{ fontWeight: 600 }}
            contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 13 }}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
          {seriesKeys.map((key, i) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
