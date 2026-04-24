import type { Metadata } from "next";
import { api } from "@/lib/api";
import { MetricCard } from "@/components/ui/metric-card";
import { LastUpdated } from "@/components/ui/last-updated";

export const metadata: Metadata = { title: "Home" };

const SECTIONS = [
  { href: "/debt-overview", title: "Debt Overview", description: "Outstanding principal stock with instrument-level provenance.", icon: "💳" },
  { href: "/debt-issuance", title: "Debt Issuance", description: "All confirmed debt issuances with dates and amounts.", icon: "📤" },
  { href: "/debt-pipeline", title: "Debt Pipeline", description: "Scheduled and notified borrowing events.", icon: "🗓" },
  { href: "/repayments", title: "Repayments", description: "Principal and coupon repayments due and settled.", icon: "↩" },
  { href: "/receipts", title: "Receipts", description: "Revenue and capital receipts including tax and non-tax.", icon: "🧾" },
  { href: "/expenditure", title: "Expenditure", description: "Revenue and capital expenditure across major heads.", icon: "💰" },
  { href: "/department-spending", title: "Department Spending", description: "Sanctioned vs actual spending by department.", icon: "🏢" },
  { href: "/deficits", title: "Deficits", description: "Fiscal, revenue and primary deficit series.", icon: "📊" },
];

export default async function Page() {
  const [debtRes, receiptsRes, expendRes, deficitRes, health] = await Promise.all([
    api.debt.outstanding({ page_size: 1 }),
    api.fiscal.receipts({ page_size: 1 }),
    api.fiscal.expenditure({ page_size: 1 }),
    api.fiscal.deficits({ page_size: 1 }),
    api.health(),
  ]);
  const now = new Date().toISOString();

  return (
    <div className="space-y-10">
      {/* Hero */}
      <section>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight text-ink">
              Andhra Pradesh Finance
            </h1>
            <p className="mt-2 text-xl font-light text-slate-500">Public Finance Transparency Platform</p>
            <p className="mt-4 max-w-2xl text-slate-600">
              Open data on government debt, receipts, expenditure, and deficits — with full
              provenance from source document to page and row. Every series is labelled as audited,
              monthly provisional, budget estimate, revised estimate, projection, or scheduled.
            </p>
          </div>
          <div className="hidden shrink-0 text-5xl sm:block" aria-hidden="true">🏛️</div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex h-2 w-2 rounded-full ${health ? "bg-emerald-400" : "bg-red-400"}`}
            title={health ? "API online" : "API offline"}
          />
          <span className="text-xs text-slate-400">
            {health ? `API: ${health.status} · ${health.environment}` : "API not reachable"}
          </span>
          <LastUpdated timestamp={now} />
        </div>
      </section>

      {/* Summary cards */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-700">At a Glance</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard title="Debt Records" value={debtRes ? debtRes.pagination.total : null} description="Outstanding debt positions published" href="/debt-overview" lastUpdated={debtRes ? now : null} />
          <MetricCard title="Receipt Records" value={receiptsRes ? receiptsRes.pagination.total : null} description="Fiscal receipt observations published" href="/receipts" lastUpdated={receiptsRes ? now : null} />
          <MetricCard title="Expenditure Records" value={expendRes ? expendRes.pagination.total : null} description="Expenditure observations published" href="/expenditure" lastUpdated={expendRes ? now : null} />
          <MetricCard title="Deficit Records" value={deficitRes ? deficitRes.pagination.total : null} description="Deficit metric observations published" href="/deficits" lastUpdated={deficitRes ? now : null} />
        </div>
      </section>

      {/* Browse by topic */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Browse by Topic</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SECTIONS.map((s) => (
            <a key={s.href} href={s.href} className="group rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm transition-shadow hover:shadow-md">
              <div className="text-2xl" aria-hidden="true">{s.icon}</div>
              <h3 className="mt-3 font-semibold text-slate-800 group-hover:text-tide">{s.title}</h3>
              <p className="mt-1 text-sm text-slate-500">{s.description}</p>
            </a>
          ))}
        </div>
      </section>

      {/* Trust notice */}
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-700">About the data</h2>
        <div className="mt-3 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
          <div>
            <span className="inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">Audited</span>
            <p className="mt-1">Final figures from CAG audit reports. Authoritative and not subject to revision.</p>
          </div>
          <div>
            <span className="inline-block rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">Provisional</span>
            <p className="mt-1">Monthly provisional releases ahead of audit. Subject to revision. Treat as indicative.</p>
          </div>
          <div>
            <span className="inline-block rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">Budget / Revised</span>
            <p className="mt-1">Government-approved estimates. Actuals will differ.</p>
          </div>
        </div>
      </section>

      {/* Reference links */}
      <section className="flex flex-wrap gap-3 text-sm">
        {[
          { href: "/sources", label: "Source Documents" },
          { href: "/methodology", label: "Methodology" },
          { href: "/changelog", label: "Changelog" },
          { href: "/api", label: "API Documentation" },
          { href: "/admin/review-queue", label: "Admin Review Queue" },
        ].map((l) => (
          <a key={l.href} href={l.href} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-slate-600 hover:border-tide hover:text-tide">
            {l.label} →
          </a>
        ))}
      </section>
    </div>
  );
}
