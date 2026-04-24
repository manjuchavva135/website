interface EmptyStateProps {
  title?: string;
  message?: string;
  /** Optional action link */
  action?: { label: string; href: string };
  /** Supply for "under review" variant */
  variant?: "no-data" | "under-review" | "filtered";
}

const VARIANT_CONFIG = {
  "no-data": {
    icon: "📭",
    title: "No data available",
    message:
      "This dataset has not yet been published. Check back after the next data release.",
  },
  "under-review": {
    icon: "🔍",
    title: "Under review",
    message:
      "Source documents for this period are in the admin review queue and will be published after approval.",
  },
  filtered: {
    icon: "🔎",
    title: "No results for these filters",
    message:
      "Try adjusting the financial year, basis, or date range to find matching records.",
  },
};

export function EmptyState({
  title,
  message,
  action,
  variant = "no-data",
}: EmptyStateProps) {
  const config = VARIANT_CONFIG[variant];
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-16 text-center">
      <span className="text-4xl" role="img" aria-hidden="true">
        {config.icon}
      </span>
      <h3 className="mt-4 text-base font-semibold text-slate-700">
        {title ?? config.title}
      </h3>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        {message ?? config.message}
      </p>
      {action && (
        <a
          href={action.href}
          className="mt-5 rounded-lg bg-tide px-4 py-2 text-sm font-medium text-white hover:bg-teal-600"
        >
          {action.label}
        </a>
      )}
    </div>
  );
}
