"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

export interface AreaDataPoint {
  label: string;
  [key: string]: string | number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value: number; name: string; color: string }[];
  label?: string;
  formatter?: (v: number) => string;
}

function CustomTooltip({ active, payload, label, formatter }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const fmt = formatter ?? ((v: number) =>
    new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(v)
  );
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-lg text-sm">
      <p className="font-semibold text-slate-700 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-medium">{fmt(p.value)}</span>
        </p>
      ))}
    </div>
  );
}

interface AreaChartClientProps {
  data: AreaDataPoint[];
  seriesKeys: string[];
  colors?: string[];
  yLabel?: string;
  height?: number;
  formatter?: (v: number) => string;
  referenceLines?: { x: string; label: string; color?: string }[];
}

const DEFAULT_COLORS = ["#0ea5a4", "#6366f1", "#f59e0b", "#10b981", "#f43f5e"];

export function AreaChartClient({
  data,
  seriesKeys,
  colors = DEFAULT_COLORS,
  yLabel,
  height = 340,
  formatter,
  referenceLines = [],
}: AreaChartClientProps) {
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
        <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <defs>
            {seriesKeys.map((key, i) => (
              <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors[i % colors.length]} stopOpacity={0.25} />
                <stop offset="95%" stopColor={colors[i % colors.length]} stopOpacity={0.02} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={fmt}
            label={
              yLabel
                ? {
                    value: yLabel,
                    angle: -90,
                    position: "insideLeft",
                    style: { fontSize: 11, fill: "#94a3b8" },
                  }
                : undefined
            }
          />
          <Tooltip
            content={
              <CustomTooltip
                formatter={
                  formatter ??
                  ((v) =>
                    new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(v))
                }
              />
            }
          />
          {referenceLines.map((rl) => (
            <ReferenceLine
              key={rl.x}
              x={rl.x}
              stroke={rl.color ?? "#94a3b8"}
              strokeDasharray="4 3"
              label={{ value: rl.label, fontSize: 10, fill: rl.color ?? "#94a3b8" }}
            />
          ))}
          {seriesKeys.map((key, i) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              name={key}
              stroke={colors[i % colors.length]}
              strokeWidth={2.5}
              fill={`url(#grad-${key})`}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 0 }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
