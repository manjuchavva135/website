import type { Metadata } from "next";

export const metadata: Metadata = { title: "Methodology" };

const LIFECYCLE_STEPS = [
  { n: "1", title: "Acquire", text: "Source artifact downloaded from RBI, AP Finance Department, or CAG and stored in object storage with SHA-256 checksum and parser version." },
  { n: "2", title: "Parse", text: "Structured extractor reads rows, tables and metadata. Every row receives document_id, page, and row references." },
  { n: "3", title: "Review", text: "Extracted rows enter the admin review queue. A human reviewer approves or rejects each document before publication." },
  { n: "4", title: "Tag", text: "Each observation is tagged with a basis label: audited, provisional, budget_estimate, revised_estimate, scheduled, projected, or issued." },
  { n: "5", title: "Publish", text: "Approved, tagged observations are served through the JSON and CSV APIs with provenance embedded in every response." },
];

const BASIS_EXPLANATIONS = [
  { basis: "Audited", color: "bg-emerald-100 text-emerald-800", text: "Final figures from CAG audit reports. Authoritative and not subject to revision." },
  { basis: "Provisional", color: "bg-orange-100 text-orange-800", text: "Released ahead of audit. Subject to revision. Treat as indicative." },
  { basis: "Budget Estimate", color: "bg-blue-100 text-blue-800", text: "Government-approved allocation for the financial year. Actuals will differ." },
  { basis: "Revised Estimate", color: "bg-amber-100 text-amber-800", text: "Mid-year revision of budget estimates. Subject to final audit." },
  { basis: "Scheduled", color: "bg-slate-100 text-slate-700", text: "Events not yet settled. Dates and amounts may change before execution." },
  { basis: "Projected", color: "bg-violet-100 text-violet-800", text: "Forward-looking model estimates. May differ materially from actuals." },
  { basis: "Issued", color: "bg-teal-100 text-teal-800", text: "Confirmed issued instruments with full provenance from official notifications." },
];

export default function MethodologyPage() {
  return (
    <div className="space-y-10 max-w-3xl">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-ink">Methodology</h1>
        <p className="mt-2 text-slate-600">
          How Andhra Pradesh public finance data is acquired, validated, labelled, and published
          on this platform.
        </p>
      </div>

      {/* Data lifecycle */}
      <section>
        <h2 className="text-xl font-semibold text-slate-800">Data Lifecycle</h2>
        <div className="mt-4 space-y-4">
          {LIFECYCLE_STEPS.map((step) => (
            <div key={step.n} className="flex gap-4 rounded-xl border border-slate-200 bg-white/80 p-4">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-tide/10 text-sm font-bold text-tide">
                {step.n}
              </span>
              <div>
                <p className="font-semibold text-slate-800">{step.title}</p>
                <p className="mt-1 text-sm text-slate-600">{step.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Basis labels */}
      <section>
        <h2 className="text-xl font-semibold text-slate-800">Basis Labels</h2>
        <p className="mt-2 text-sm text-slate-600">
          Every metric on this platform carries a basis label. No unlabelled or mixed series are
          published. A single page may show multiple bases — use the filter to isolate one.
        </p>
        <div className="mt-4 space-y-3">
          {BASIS_EXPLANATIONS.map((b) => (
            <div key={b.basis} className="flex items-start gap-3">
              <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${b.color}`}>
                {b.basis}
              </span>
              <p className="text-sm text-slate-600">{b.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Data sources */}
      <section>
        <h2 className="text-xl font-semibold text-slate-800">Primary Sources</h2>
        <ul className="mt-4 space-y-2 text-sm text-slate-600">
          <li className="rounded-lg border border-slate-200 bg-white/80 px-4 py-3">
            <span className="font-medium">Reserve Bank of India (RBI)</span> — State finances data, debt statistics, and monetary policy reports published annually and monthly.
          </li>
          <li className="rounded-lg border border-slate-200 bg-white/80 px-4 py-3">
            <span className="font-medium">AP Finance Department</span> — Budget documents, appropriation accounts, and mid-year revision statements.
          </li>
          <li className="rounded-lg border border-slate-200 bg-white/80 px-4 py-3">
            <span className="font-medium">Comptroller and Auditor General (CAG)</span> — Audit reports providing the final, authoritative figures for each financial year.
          </li>
        </ul>
      </section>

      {/* Limitations */}
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
        <h2 className="font-semibold">Known Limitations</h2>
        <ul className="mt-2 list-disc space-y-1 pl-4">
          <li>Historical data before 2016-17 may be incomplete or unavailable in machine-readable form.</li>
          <li>Department-level breakdowns may not sum exactly to state totals due to rounding in source documents.</li>
          <li>Scheduled events reflect official notifications and may be amended before settlement.</li>
        </ul>
      </section>
    </div>
  );
}

