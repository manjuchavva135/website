import type { Metadata } from "next";
import { api } from "@/lib/api";
import { LastUpdated } from "@/components/ui/last-updated";
import { MetricCard } from "@/components/ui/metric-card";
import { PageError } from "@/components/ui/page-error";
import { AreaChartClient } from "@/components/charts/area-chart-client";
import { ComboChartClient } from "@/components/charts/combo-chart-client";
import { BarChartClient, type BarDataPoint } from "@/components/charts/bar-chart-client";
import { PeerCompareToggle } from "@/components/ui/peer-compare-toggle";

export const metadata: Metadata = { title: "Debt Overview" };

const fmtCrore = (v: number) =>
  "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr";

const fmtLakhCrore = (v: number) =>
  "₹" + (v / 100000).toFixed(2) + " L Cr";

export default async function DebtOverviewPage() {
  const [summary, maturity, composition] = await Promise.all([
    api.debt.summary(),
    api.debt.maturitySchedule(),
    api.ap.debtComposition(),
  ]);

  const now = new Date().toISOString();

  if (!summary) return <PageError retryHref="/debt-overview" />;

  const current = summary.current_outstanding;
  const latestYoY = summary.year_over_year.at(-1);

  // Chart data: historical outstanding
  const historicalData = summary.historical_outstanding.map((d) => ({
    label: d.fiscal_year,
    "Outstanding (₹ Cr)": d.value,
  }));

  // Year-over-year increase chart data
  const yoyData = summary.year_over_year.map((d) => ({
    label: d.fiscal_year,
    "Annual Increase (₹ Cr)": d.increase,
    "Growth %": d.increase_pct,
  }));

  // Borrowings breakdown for the last 3 years
  const bkKeys = [
    "market_borrowings_gross_raised",
    "loans_from_centre_gross",
    "market_borrowings_repayments",
    "interest_payments_gross",
  ];
  const bkLabels: Record<string, string> = {
    market_borrowings_gross_raised: "Market Borrowings",
    loans_from_centre_gross: "Loans from Centre",
    market_borrowings_repayments: "Market Repayments",
    interest_payments_gross: "Interest Payments",
  };
  // Pivot: one row per FY
  const bkFYs = Array.from(
    new Set(
      bkKeys.flatMap((k) => (summary.breakdown[k] ?? []).map((d) => d.fiscal_year))
    )
  ).sort();
  const bkData = bkFYs.map((fy) => {
    const row: BarDataPoint = { label: fy };
    for (const k of bkKeys) {
      const match = (summary.breakdown[k] ?? []).find((d) => d.fiscal_year === fy);
      row[bkLabels[k]] = match?.value ?? 0;
    }
    return row;
  });

  // Maturity schedule data
  const maturityData = (maturity?.schedule ?? []).slice(0, 20).map((d) => ({
    label: d.fiscal_year,
    "Principal Due (₹ Cr)": d.principal_due,
  }));

  const totalMaturity = maturity?.total ?? 0;

  return (
    <div className="space-y-8">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Debt Overview</h1>
          <p className="mt-1 text-slate-500">
            Andhra Pradesh — total outstanding liabilities and debt trajectory (2007–08 to 2025–26)
          </p>
          <LastUpdated timestamp={now} className="mt-1" />
        </div>
        <span className="inline-flex items-center rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700 ring-1 ring-inset ring-teal-200">
          Source: AP Budget Documents
        </span>
      </div>

      {/* ── KPI Cards ─────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Outstanding Debt"
          value={current ? fmtLakhCrore(current.value) : "—"}
          description={`As of FY ${current?.fiscal_year ?? "—"}`}
          lastUpdated={now}
        />
        <MetricCard
          title="Annual Increase"
          value={latestYoY ? fmtCrore(latestYoY.increase) : "—"}
          description={`Added in FY ${latestYoY?.fiscal_year ?? "—"}`}
          delta={latestYoY ? { value: `${latestYoY.increase_pct.toFixed(1)}%`, direction: "up" } : undefined}
          lastUpdated={now}
        />
        <MetricCard
          title="Debt Growth (18 yrs)"
          value={
            summary.historical_outstanding.length >= 2
              ? `${(
                  ((summary.historical_outstanding.at(-1)!.value -
                    summary.historical_outstanding[0].value) /
                    summary.historical_outstanding[0].value) *
                  100
                ).toFixed(0)}%`
              : "—"
          }
          description={`Since FY ${summary.historical_outstanding[0]?.fiscal_year ?? "—"}`}
          lastUpdated={now}
        />
        <MetricCard
          title="SDL Maturities Outstanding"
          value={totalMaturity ? fmtLakhCrore(totalMaturity) : "—"}
          description="Total SDL principal due (from Outstanding Securities)"
          lastUpdated={now}
        />
      </div>

      {/* ── Historical Debt Growth Chart ───────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">
          Total Outstanding Liabilities — FY 2007–08 to 2025–26
        </h2>
        <p className="mb-5 text-xs text-slate-500">
          Source: AP Budget Documents (Volumes I &amp; II), Audited Actuals &amp; Budget Estimates
        </p>
        <AreaChartClient
          data={historicalData}
          seriesKeys={["Outstanding (₹ Cr)"]}
          colors={["#0ea5a4"]}
          yLabel="₹ Crore"
          height={360}
          referenceLines={[{ x: "2014-15", label: "State bifurcation", color: "#f43f5e" }]}
        />
        <div className="mt-4">
          <PeerCompareToggle
            metricCode="total_outstanding_liabilities_pct_gsdp"
            label="Debt-to-GSDP (%)"
            fiscalYear={current?.fiscal_year ?? "2023-24"}
            formatPreset="pct1"
          />
        </div>
      </div>

      {/* ── Year-over-Year Increase ────────────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">
          Year-on-Year Debt Increase
        </h2>
        <p className="mb-5 text-xs text-slate-500">
          Annual addition to total outstanding liabilities with growth rate (%)
        </p>
        <ComboChartClient
          data={yoyData}
          barKey="Annual Increase (₹ Cr)"
          barLabel="Annual Increase (₹ Cr)"
          lineKey="Growth %"
          lineLabel="Growth %"
          barColor="#6366f1"
          lineColor="#f59e0b"
          yLabel="₹ Crore"
          y2Label="Growth %"
          height={320}
          lineUnit="%"
        />
      </div>

      {/* ── Debt Composition ──────────────────────────────────────── */}
      {composition && composition.components.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <h2 className="mb-1 text-base font-semibold text-slate-800">
            Debt Composition — FY {composition.fiscal_year ?? "Latest"}
          </h2>
          <p className="mb-5 text-xs text-slate-500">
            Breakdown of total outstanding liabilities by instrument type
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-slate-600">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="py-2 pr-6 text-left font-semibold text-slate-700">Component</th>
                  <th className="py-2 pr-6 text-right font-semibold text-slate-700">Value (₹ Cr)</th>
                  <th className="py-2 text-right font-semibold text-slate-700">Share</th>
                </tr>
              </thead>
              <tbody>
                {composition.components.map((c) => (
                  <tr key={c.metric_code} className="border-b border-slate-50 hover:bg-slate-50/60">
                    <td className="py-2 pr-6">{c.label}</td>
                    <td className="py-2 pr-6 text-right font-medium">
                      {c.value != null ? fmtCrore(c.value) : "—"}
                    </td>
                    <td className="py-2 text-right text-slate-400">
                      {c.value != null && composition.total
                        ? ((c.value / composition.total) * 100).toFixed(1) + "%"
                        : "—"}
                    </td>
                  </tr>
                ))}
                {composition.total && (
                  <tr className="border-t border-slate-200 font-semibold text-slate-700">
                    <td className="py-2 pr-6">Total</td>
                    <td className="py-2 pr-6 text-right">{fmtCrore(composition.total)}</td>
                    <td className="py-2 text-right">100%</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Borrowings & Repayments Breakdown ─────────────────────── */}
      {bkData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <h2 className="mb-1 text-base font-semibold text-slate-800">
            Borrowings &amp; Debt Service Breakdown
          </h2>
          <p className="mb-5 text-xs text-slate-500">
            Market borrowings raised vs. repaid, loans from Centre, and interest payments (FY 2023–24 to 2025–26)
          </p>
          <BarChartClient
            data={bkData}
            dataKey="Market Borrowings"
            dataKey2="Interest Payments"
            color="#0ea5a4"
            color2="#f43f5e"
            height={300}
          />
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-xs text-slate-600">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="py-2 pr-4 text-left font-semibold text-slate-700">FY</th>
                  {Object.values(bkLabels).map((l) => (
                    <th key={l} className="py-2 pr-4 text-right font-semibold text-slate-700">{l}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bkData.map((row) => (
                  <tr key={row.label as string} className="border-b border-slate-50 hover:bg-slate-50/60">
                    <td className="py-2 pr-4 font-medium">{row.label}</td>
                    {Object.values(bkLabels).map((l) => (
                      <td key={l} className="py-2 pr-4 text-right">
                        {typeof row[l] === "number" && (row[l] as number) > 0
                          ? fmtCrore(row[l] as number)
                          : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── SDL Maturity / Repayment Schedule ────────────────────── */}
      {maturityData.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <h2 className="mb-1 text-base font-semibold text-slate-800">
            State Development Loan (SDL) Repayment Schedule
          </h2>
          <p className="mb-5 text-xs text-slate-500">
            Principal due per fiscal year from Outstanding Securities data — shows when existing SDL debt matures
          </p>
          <BarChartClient
            data={maturityData}
            dataKey="Principal Due (₹ Cr)"
            color="#f59e0b"
            height={320}
            horizontal={maturityData.length > 12}
          />
          <p className="mt-3 text-xs text-slate-400">
            Total SDL outstanding: {fmtLakhCrore(totalMaturity)} across {maturity?.schedule.length ?? 0} fiscal years
          </p>
        </div>
      )}

      {/* ── Data Notes ────────────────────────────────────────────── */}
      <div className="rounded-xl bg-slate-50 border border-slate-200 px-5 py-4 text-xs text-slate-500 space-y-1">
        <p className="font-semibold text-slate-600">Data Sources &amp; Notes</p>
        <p>• Outstanding Liabilities (2007–08 to 2025–26): AP Budget Documents, Appendix tables — audited actuals up to 2023–24, budget estimates for 2024–25 and 2025–26.</p>
        <p>• State bifurcation (2014–15): AP was bifurcated in June 2014; figures from 2014–15 onwards reflect residual Andhra Pradesh only.</p>
        <p>• SDL Maturity Schedule: Reserve Bank of India Outstanding Securities data (as of May 2026).</p>
        <p>• All values in Indian Rupee Crore (₹ Cr). 1 Lakh Crore = ₹1 Trillion.</p>
      </div>
    </div>
  );
}
