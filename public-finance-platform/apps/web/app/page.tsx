import type { Metadata } from "next";
import { api } from "@/lib/api";
import { MetricCard } from "@/components/ui/metric-card";
import { LastUpdated } from "@/components/ui/last-updated";
import { PeerCompareToggle } from "@/components/ui/peer-compare-toggle";

export const metadata: Metadata = { title: "Andhra Pradesh Public Finance" };

const SECTIONS = [
  { href: "/debt-overview", title: "Debt Overview", description: "Outstanding liabilities with historical trend and peer comparison.", icon: "💳" },
  { href: "/debt-stack", title: "Debt Stack", description: "Per-instrument SDL list — ISIN, coupon, maturity, outstanding.", icon: "📋" },
  { href: "/repayments", title: "Repayments", description: "SDL maturity schedule and annual principal due.", icon: "↩" },
  { href: "/receipts", title: "Receipts", description: "Revenue and capital receipts including tax and non-tax.", icon: "🧾" },
  { href: "/expenditure", title: "Expenditure", description: "Revenue and capital expenditure across major heads.", icon: "💰" },
  { href: "/deficits", title: "Deficits", description: "Fiscal, revenue and primary deficit series.", icon: "📊" },
  { href: "/department-spending", title: "Department Spending", description: "Sanctioned vs actual spending by department.", icon: "🏢" },
  { href: "/debt-issuance", title: "Debt Issuance", description: "All confirmed debt issuances with dates and amounts.", icon: "📤" },
];

const fmtLakhCrore = (v: number) =>
  "₹" + (v / 100000).toFixed(2) + " L Cr";

const fmtCrore = (v: number) =>
  "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr";

export default async function Page() {
  const [headline, health] = await Promise.all([
    api.ap.headline(),
    api.health(),
  ]);
  const now = new Date().toISOString();

  // Extract key headline metrics
  const metrics = headline?.metrics ?? [];
  const getMetric = (code: string) => metrics.find((m) => m.metric_code === code);

  const totalDebt = getMetric("total_outstanding_liabilities");
  const debtGsdp = getMetric("total_outstanding_liabilities_pct_gsdp");
  const fiscalDeficit = getMetric("gross_fiscal_deficit");
  const revenueDeficit = getMetric("revenue_deficit");

  return (
    <div className="space-y-10">
      {/* ── Hero ──────────────────────────────────────────────────── */}
      <section>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight text-ink">
              Andhra Pradesh Finance
            </h1>
            <p className="mt-2 text-xl font-light text-slate-500">
              Public Finance Transparency Platform
            </p>
            <p className="mt-4 max-w-2xl text-slate-600">
              Open data on Andhra Pradesh government debt, receipts, expenditure, and deficits —
              sourced from RBI State Finances and AP Budget documents, with full provenance from
              source document to row. Every figure is labelled as audited, revised estimate, budget
              estimate, or provisional.
            </p>
          </div>
          <div className="hidden shrink-0 text-5xl sm:block" aria-hidden="true">
            🏛️
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex h-2 w-2 rounded-full ${health ? "bg-emerald-400" : "bg-red-400"}`}
            title={health ? "API online" : "API offline"}
          />
          <span className="text-xs text-slate-400">
            {health
              ? `API: ${health.status} · ${health.environment}`
              : "API not reachable"}
          </span>
          <LastUpdated timestamp={now} />
        </div>
      </section>

      {/* ── AP Headline KPIs ──────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-700">
          Andhra Pradesh — At a Glance
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Total Outstanding Debt"
            value={totalDebt?.value != null ? fmtLakhCrore(totalDebt.value) : null}
            basis={totalDebt?.basis_tag}
            description={totalDebt?.fiscal_year ? `FY ${totalDebt.fiscal_year}` : undefined}
            href="/debt-overview"
            lastUpdated={totalDebt ? now : null}
          />
          <MetricCard
            title="Debt-to-GSDP"
            value={debtGsdp?.value != null ? `${debtGsdp.value.toFixed(1)}%` : null}
            basis={debtGsdp?.basis_tag}
            description={debtGsdp?.fiscal_year ? `FY ${debtGsdp.fiscal_year}` : undefined}
            href="/debt-overview"
            lastUpdated={debtGsdp ? now : null}
          />
          <MetricCard
            title="Gross Fiscal Deficit"
            value={fiscalDeficit?.value != null ? fmtCrore(fiscalDeficit.value) : null}
            basis={fiscalDeficit?.basis_tag}
            description={fiscalDeficit?.fiscal_year ? `FY ${fiscalDeficit.fiscal_year}` : undefined}
            href="/deficits"
            lastUpdated={fiscalDeficit ? now : null}
          />
          <MetricCard
            title="Revenue Deficit"
            value={revenueDeficit?.value != null ? fmtCrore(revenueDeficit.value) : null}
            basis={revenueDeficit?.basis_tag}
            description={revenueDeficit?.fiscal_year ? `FY ${revenueDeficit.fiscal_year}` : undefined}
            href="/deficits"
            lastUpdated={revenueDeficit ? now : null}
          />
        </div>
      </section>

      {/* ── How AP Compares ───────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">How AP Compares</h2>
        <p className="mb-4 text-xs text-slate-500">
          Andhra Pradesh debt-to-GSDP ratio vs. major states — toggle to explore.
        </p>
        <PeerCompareToggle
          metricCode="total_outstanding_liabilities_pct_gsdp"
          label="Debt-to-GSDP (%)"
          fiscalYear={debtGsdp?.fiscal_year ?? "2023-24"}
          formatPreset="pct1"
        />
      </section>

      {/* ── Browse by topic ───────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Browse by Topic</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SECTIONS.map((s) => (
            <a
              key={s.href}
              href={s.href}
              className="group rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="text-2xl" aria-hidden="true">
                {s.icon}
              </div>
              <h3 className="mt-3 font-semibold text-slate-800 group-hover:text-tide">
                {s.title}
              </h3>
              <p className="mt-1 text-sm text-slate-500">{s.description}</p>
            </a>
          ))}
        </div>
      </section>

      {/* ── Trust notice ──────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-700">About the data</h2>
        <div className="mt-3 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
          <div>
            <span className="inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
              Audited
            </span>
            <p className="mt-1">
              Final figures from CAG audit reports. Authoritative and not subject to revision.
            </p>
          </div>
          <div>
            <span className="inline-block rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
              Provisional
            </span>
            <p className="mt-1">
              Monthly provisional releases ahead of audit. Subject to revision. Treat as
              indicative.
            </p>
          </div>
          <div>
            <span className="inline-block rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
              Budget / Revised
            </span>
            <p className="mt-1">Government-approved estimates. Actuals will differ.</p>
          </div>
        </div>
      </section>

      {/* ── Reference links ───────────────────────────────────────── */}
      <section className="flex flex-wrap gap-3 text-sm">
        {[
          { href: "/sources", label: "Source Documents" },
          { href: "/methodology", label: "Methodology" },
          { href: "/changelog", label: "Changelog" },
          { href: "/api-docs", label: "API Documentation" },
          { href: "/admin/review-queue", label: "Admin" },
        ].map((l) => (
          <a
            key={l.href}
            href={l.href}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-slate-600 hover:border-tide hover:text-tide"
          >
            {l.label} →
          </a>
        ))}
      </section>
    </div>
  );
}
