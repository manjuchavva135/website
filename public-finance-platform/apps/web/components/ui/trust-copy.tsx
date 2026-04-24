type TrustLevel =
  | "audited_actual"
  | "actual"
  | "monthly_actual_provisional"
  | "quarter_actual"
  | "budget_estimate"
  | "revised_estimate"
  | "scheduled"
  | "projection"
  | "issued"
  | "notified"
  | "due"
  | "paid"
  | "nowcast"
  | string;

const TRUST_CONFIG: Record<
  string,
  { icon: string; color: string; text: string }
> = {
  audited_actual: {
    icon: "✓",
    color: "border-emerald-200 bg-emerald-50 text-emerald-800",
    text: "These figures have been audited by the Comptroller and Auditor General of India (CAG). Data is final and authoritative.",
  },
  monthly_actual_provisional: {
    icon: "⚠",
    color: "border-orange-200 bg-orange-50 text-orange-800",
    text: "Provisional data pending audit completion. Figures are subject to revision. Do not treat as final.",
  },
  quarter_actual: {
    icon: "◔",
    color: "border-sky-200 bg-sky-50 text-sky-800",
    text: "Quarterly actuals can be updated during year-end reconciliation.",
  },
  actual: {
    icon: "●",
    color: "border-cyan-200 bg-cyan-50 text-cyan-800",
    text: "Actual reported values from official systems, pending final audit confirmation.",
  },
  budget_estimate: {
    icon: "📋",
    color: "border-blue-200 bg-blue-50 text-blue-800",
    text: "Budget estimates represent the Government of Andhra Pradesh's planned allocation for the financial year. Actuals will differ.",
  },
  revised_estimate: {
    icon: "🔄",
    color: "border-amber-200 bg-amber-50 text-amber-800",
    text: "Revised estimates updated mid-year based on revised projections. Subject to final audit.",
  },
  scheduled: {
    icon: "🗓",
    color: "border-slate-200 bg-slate-50 text-slate-700",
    text: "Scheduled events have not yet occurred. Dates, amounts and counterparties may change before settlement.",
  },
  projection: {
    icon: "📈",
    color: "border-violet-200 bg-violet-50 text-violet-800",
    text: "Model-based projections. Forward-looking estimates that may differ materially from actuals.",
  },
  notified: {
    icon: "📣",
    color: "border-indigo-200 bg-indigo-50 text-indigo-800",
    text: "Notified values are official announcements and may differ from settled issuance.",
  },
  issued: {
    icon: "✓",
    color: "border-teal-200 bg-teal-50 text-teal-800",
    text: "Confirmed issued instruments with full provenance from official notifications.",
  },
  due: {
    icon: "⏳",
    color: "border-rose-200 bg-rose-50 text-rose-800",
    text: "Amounts marked due reflect scheduled obligations, not necessarily paid settlement.",
  },
  paid: {
    icon: "✔",
    color: "border-lime-200 bg-lime-50 text-lime-800",
    text: "Paid values represent settled cash outflows in official records.",
  },
  nowcast: {
    icon: "✦",
    color: "border-fuchsia-200 bg-fuchsia-50 text-fuchsia-800",
    text: "Nowcast values are near-real-time statistical estimates and can revise as official data arrives.",
  },
};

interface TrustCopyProps {
  basis?: TrustLevel | null;
  className?: string;
}

export function TrustCopy({ basis, className = "" }: TrustCopyProps) {
  if (!basis) return null;
  const config = TRUST_CONFIG[basis];
  if (!config) return null;
  return (
    <div
      role="note"
      className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${config.color} ${className}`}
    >
      <span className="mt-0.5 shrink-0 text-base leading-none" aria-hidden="true">
        {config.icon}
      </span>
      <p>{config.text}</p>
    </div>
  );
}
