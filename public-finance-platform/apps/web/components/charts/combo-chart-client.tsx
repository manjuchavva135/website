"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export interface ComboDataPoint {
  label: string;
  [key: string]: string | number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value: number; name: string; color: string; unit?: string }[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const fmtCrore = (v: number) =>
    "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr";
  const fmtPct = (v: number) => v.toFixed(1) + "%";
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-lg text-sm min-w-[180px]">
      <p className="font-semibold text-slate-700 mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="mb-0.5">
          {p.name}:{" "}
          <span className="font-medium">
            {p.unit === "%" ? fmtPct(p.value) : fmtCrore(p.value)}
          </span>
        </p>
      ))}
    </div>
  );
}

interface ComboChartClientProps {
  data: ComboDataPoint[];
  barKey: string;
  barLabel?: string;
  lineKey?: string;
  lineLabel?: string;
  barColor?: string;
  lineColor?: string;
  yLabel?: string;
  y2Label?: string;
  height?: number;
  lineUnit?: string;
}

export function ComboChartClient({
  data,
  barKey,
  barLabel,
  lineKey,
  lineLabel,
  barColor = "#0ea5a4",
  lineColor = "#f59e0b",
  yLabel,
  y2Label,
  height = 320,
  lineUnit,
}: ComboChartClientProps) {
  const fmt = (v: number) =>
    new Intl.NumberFormat("en-IN", { notation: "compact", compactDisplay: "short" }).format(v);

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
        <ComposedChart data={data} margin={{ top: 8, right: 40, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#64748b" }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            yAxisId="left"
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
          {lineKey && (
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => v.toFixed(0) + "%"}
              label={
                y2Label
                  ? {
                      value: y2Label,
                      angle: 90,
                      position: "insideRight",
                      style: { fontSize: 11, fill: "#94a3b8" },
                    }
                  : undefined
              }
            />
          )}
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 12, color: "#64748b" }}
          />
          <Bar
            yAxisId="left"
            dataKey={barKey}
            name={barLabel ?? barKey}
            fill={barColor}
            radius={[3, 3, 0, 0]}
            opacity={0.85}
          />
          {lineKey && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey={lineKey}
              name={lineLabel ?? lineKey}
              stroke={lineColor}
              strokeWidth={2.5}
              dot={{ r: 3, fill: lineColor }}
              activeDot={{ r: 5, strokeWidth: 0 }}
              unit={lineUnit}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
