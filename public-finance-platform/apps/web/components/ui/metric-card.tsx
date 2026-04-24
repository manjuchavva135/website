import { BasisBadge } from "./basis-badge";
import { LastUpdated } from "./last-updated";

interface Delta {
  value: string;
  direction: "up" | "down" | "neutral";
}

interface MetricCardProps {
  title: string;
  value: string | number | null;
  unit?: string;
  basis?: string | null;
  lastUpdated?: string | null;
  delta?: Delta;
  href?: string;
  description?: string;
  className?: string;
}

const DELTA_COLORS: Record<string, string> = {
  up: "text-emerald-600",
  down: "text-red-600",
  neutral: "text-slate-500",
};

const DELTA_ARROWS: Record<string, string> = {
  up: "↑",
  down: "↓",
  neutral: "→",
};

export function MetricCard({
  title,
  value,
  unit,
  basis,
  lastUpdated,
  delta,
  href,
  description,
  className = "",
}: MetricCardProps) {
  const isEmpty = value === null || value === undefined || value === "";

  const content = (
    <div
      className={`rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm backdrop-blur transition-shadow hover:shadow-md ${className}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-slate-600">{title}</p>
        {basis && <BasisBadge basis={basis} />}
      </div>

      <div className="mt-3 flex items-end gap-2">
        {isEmpty ? (
          <span className="text-2xl font-semibold text-slate-300">—</span>
        ) : (
          <span className="text-2xl font-semibold tracking-tight text-ink">
            {typeof value === "number" ? value.toLocaleString("en-IN") : value}
          </span>
        )}
        {unit && !isEmpty && (
          <span className="mb-0.5 text-sm text-slate-500">{unit}</span>
        )}
      </div>

      {delta && (
        <p className={`mt-1 text-xs font-medium ${DELTA_COLORS[delta.direction]}`}>
          {DELTA_ARROWS[delta.direction]} {delta.value}
        </p>
      )}

      {description && (
        <p className="mt-2 text-xs text-slate-500">{description}</p>
      )}

      <LastUpdated timestamp={lastUpdated} className="mt-3" />
    </div>
  );

  if (href) {
    return (
      <a href={href} className="block">
        {content}
      </a>
    );
  }
  return content;
}
