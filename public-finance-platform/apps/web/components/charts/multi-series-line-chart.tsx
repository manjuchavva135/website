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

export interface MultiSeriesPoint {
  label: string;
  [key: string]: string | number | null;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value: number | null; name: string; color: string }[];
  label?: string;
  formatter?: (v: number) => string;
}

function CustomTooltip({ active, payload, label, formatter }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const fmt =
    formatter ??
    ((v: number) =>
      new Intl.NumberFormat("en-IN", { notation: "compact", compactDisplay: "short" }).format(v));
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-lg text-sm min-w-[180px]">
      <p className="font-semibold text-slate-700 mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="mb-0.5">
          {p.name}:{" "}
          <span className="font-medium">{p.value != null ? fmt(p.value) : "—"}</span>
        </p>
      ))}
    </div>
  );
}

interface MultiSeriesLineChartProps {
  data: MultiSeriesPoint[];
  seriesKeys: string[];
  colors?: string[];
  height?: number;
  formatter?: (v: number) => string;
  connectNulls?: boolean;
}

const DEFAULT_COLORS = [
  "#0ea5a4",
  "#6366f1",
  "#f59e0b",
  "#10b981",
  "#f43f5e",
  "#8b5cf6",
  "#ec4899",
];

export function MultiSeriesLineChart({
  data,
  seriesKeys,
  colors = DEFAULT_COLORS,
  height = 320,
  formatter,
  connectNulls = true,
}: MultiSeriesLineChartProps) {
  const fmt =
    formatter ??
    ((v: number) =>
      new Intl.NumberFormat("en-IN", { notation: "compact", compactDisplay: "short" }).format(v));

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-400">
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
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tickFormatter={fmt}
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickLine={false}
            axisLine={false}
            width={60}
          />
          <Tooltip content={<CustomTooltip formatter={formatter} />} />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          {seriesKeys.map((key, i) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5 }}
              connectNulls={connectNulls}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
