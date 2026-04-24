export function PageLoading() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading…" role="status">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="h-8 w-64 rounded-lg bg-slate-200" />
        <div className="h-4 w-40 rounded bg-slate-100" />
      </div>
      {/* Filter bar skeleton */}
      <div className="flex gap-3">
        <div className="h-9 w-40 rounded-lg bg-slate-200" />
        <div className="h-9 w-40 rounded-lg bg-slate-200" />
        <div className="h-9 w-24 rounded-lg bg-slate-100" />
      </div>
      {/* Metric cards skeleton */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-2xl border border-slate-200 bg-white/80 p-5">
            <div className="h-4 w-24 rounded bg-slate-200" />
            <div className="mt-3 h-8 w-32 rounded bg-slate-200" />
            <div className="mt-2 h-3 w-20 rounded bg-slate-100" />
          </div>
        ))}
      </div>
      {/* Chart skeleton */}
      <div className="h-64 rounded-2xl border border-slate-200 bg-white/80 p-4">
        <div className="h-full rounded bg-slate-100" />
      </div>
      {/* Table skeleton */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 overflow-hidden">
        <div className="h-10 w-full bg-slate-100" />
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="flex gap-4 border-t border-slate-100 px-4 py-3"
          >
            <div className="h-4 flex-1 rounded bg-slate-100" />
            <div className="h-4 w-24 rounded bg-slate-100" />
            <div className="h-4 w-20 rounded bg-slate-200" />
          </div>
        ))}
      </div>
    </div>
  );
}
