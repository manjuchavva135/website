"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";

export interface BarDataPoint {
  label: string;
  [key: string]: string | number;
}

interface BarChartClientProps {
  data: BarDataPoint[];
  dataKey: string;
  /** Optional second data key for grouped bars */
  dataKey2?: string;
  color?: string;
  color2?: string;
  yLabel?: string;
  height?: number;
  horizontal?: boolean;
}

export function BarChartClient({
  data,
  dataKey,
  dataKey2,
  color = "#0ea5a4",
  color2 = "#6366f1",
  yLabel,
  height = 300,
  horizontal = false,
}: BarChartClientProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-400">
        No data to display
      </div>
    );
  }

  const fmt = (v: number) =>
    new Intl.NumberFormat("en-IN", { notation: "compact", compactDisplay: "short" }).format(v);

  const commonAxis = {
    tick: { fontSize: 12, fill: "#64748b" },
    tickLine: false,
    axisLine: false,
  };

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout={horizontal ? "vertical" : "horizontal"}
          margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          {horizontal ? (
            <>
              <XAxis type="number" {...commonAxis} tickFormatter={fmt} />
              <YAxis type="category" dataKey="label" {...commonAxis} width={120} />
            </>
          ) : (
            <>
              <XAxis dataKey="label" {...commonAxis} />
              <YAxis
                {...commonAxis}
                tickFormatter={fmt}
                label={
                  yLabel
                    ? { value: yLabel, angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#94a3b8" } }
                    : undefined
                }
              />
            </>
          )}
          <Tooltip
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(value: any) =>
              typeof value === "number"
                ? new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(value)
                : String(value ?? "")
            }
            contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 13 }}
          />
          {dataKey2 && <Legend iconType="square" iconSize={10} wrapperStyle={{ fontSize: 12 }} />}
          <Bar dataKey={dataKey} fill={color} radius={[3, 3, 0, 0]} maxBarSize={48}>
            {!dataKey2 &&
              data.map((_, i) => (
                <Cell key={i} fill={color} fillOpacity={0.85 + (i % 3) * 0.05} />
              ))}
          </Bar>
          {dataKey2 && (
            <Bar dataKey={dataKey2} fill={color2} radius={[3, 3, 0, 0]} maxBarSize={48} />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
