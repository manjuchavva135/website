export type Basis =
  | "audited_actual"
  | "actual"
  | "monthly_actual_provisional"
  | "quarter_actual"
  | "budget_estimate"
  | "revised_estimate"
  | "projection"
  | "scheduled"
  | "notified"
  | "issued"
  | "due"
  | "paid"
  | "nowcast"
  | string;

const COLOR_MAP: Record<string, string> = {
  audited_actual: "bg-emerald-100 text-emerald-800 border-emerald-200",
  actual: "bg-cyan-100 text-cyan-800 border-cyan-200",
  monthly_actual_provisional: "bg-orange-100 text-orange-800 border-orange-200",
  quarter_actual: "bg-sky-100 text-sky-800 border-sky-200",
  budget_estimate: "bg-blue-100 text-blue-800 border-blue-200",
  revised_estimate: "bg-amber-100 text-amber-800 border-amber-200",
  projection: "bg-violet-100 text-violet-800 border-violet-200",
  scheduled: "bg-slate-100 text-slate-700 border-slate-300",
  notified: "bg-indigo-100 text-indigo-800 border-indigo-200",
  issued: "bg-teal-100 text-teal-800 border-teal-200",
  due: "bg-rose-100 text-rose-800 border-rose-200",
  paid: "bg-lime-100 text-lime-800 border-lime-200",
  nowcast: "bg-fuchsia-100 text-fuchsia-800 border-fuchsia-200",
};

const LABEL_MAP: Record<string, string> = {
  audited_actual: "Audited",
  actual: "Actual",
  monthly_actual_provisional: "Monthly Provisional",
  quarter_actual: "Quarter Actual",
  budget_estimate: "Budget Est.",
  revised_estimate: "Revised Est.",
  projection: "Projection",
  scheduled: "Scheduled",
  notified: "Notified",
  issued: "Issued",
  due: "Due",
  paid: "Paid",
  nowcast: "Nowcast",
};

interface BasisBadgeProps {
  basis?: string | null;
  className?: string;
  size?: "sm" | "md";
}

export function BasisBadge({ basis, className = "", size = "sm" }: BasisBadgeProps) {
  if (!basis) return null;
  const colors = COLOR_MAP[basis] ?? "bg-slate-100 text-slate-700 border-slate-200";
  const label = LABEL_MAP[basis] ?? basis.replace(/_/g, " ");
  const sizeClass = size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-2.5 py-1";
  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium ${sizeClass} ${colors} ${className}`}
      title={`Data basis: ${basis}`}
    >
      {label}
    </span>
  );
}
