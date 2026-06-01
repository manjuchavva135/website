import type { Metadata } from "next";
import { api } from "@/lib/api";
import { LastUpdated } from "@/components/ui/last-updated";
import { MetricCard } from "@/components/ui/metric-card";
import { PageError } from "@/components/ui/page-error";
import { BarChartClient } from "@/components/charts/bar-chart-client";
import { AreaChartClient } from "@/components/charts/area-chart-client";

export const metadata: Metadata = { title: "Repayments" };

const fmtCrore = (v: number) =>
  "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(v) + " Cr";
const fmtLakhCrore = (v: number) =>
  "₹" + (v / 100000).toFixed(2) + " L Cr";

export default async function RepaymentsPage() {
  const [maturity, summary, stack] = await Promise.all([
    api.debt.maturitySchedule(),
    api.debt.summary(),
    api.debt.stack({ state_code: "AP", page_size: 1 }),
  ]);

  const now = new Date().toISOString();

  if (!maturity) return <PageError retryHref="/repayments" />;

  const schedule = maturity.schedule;
  const total = maturity.total;

  // Near-term (next 5 years) vs long-term
  const nearTerm = schedule.filter((d) => d.fiscal_year <= "2029-30");
  const nearTermTotal = nearTerm.reduce((s, d) => s + d.principal_due, 0);

  // Chart data — full schedule
  const scheduleBarData = schedule.slice(0, 25).map((d) => ({
    label: d.fiscal_year,
    "Principal Due (₹ Cr)": d.principal_due,
  }));

  // Cumulative repayment area chart
  let cumulative = 0;
  const cumulativeData = schedule.slice(0, 25).map((d) => {
    cumulative += d.principal_due;
    return {
      label: d.fiscal_year,
      "Cumulative (₹ Cr)": cumulative,
      "Annual Due (₹ Cr)": d.principal_due,
    };
  });

  // Budget-side repayments from summary breakdown
  const budgetRepayments = summary?.breakdown["market_borrowings_repayments"] ?? [];
  const interestPayments = summary?.breakdown["interest_payments_gross"] ?? [];

  // Combine principal + interest per fiscal year (budget side)
  const principalByYear = new Map(budgetRepayments.map((d) => [d.fiscal_year, d.value]));
  const interestByYear = new Map(interestPayments.map((d) => [d.fiscal_year, d.value]));
  const debtServiceYears = Array.from(
    new Set([...principalByYear.keys(), ...interestByYear.keys()])
  ).sort();
  const debtServiceRows = debtServiceYears.map((fy) => {
    const principal = principalByYear.get(fy) ?? 0;
    const interest = interestByYear.get(fy) ?? 0;
    return { fy, principal, interest, total: principal + interest };
  });
  const debtServiceChartData = debtServiceRows.map((r) => ({
    label: r.fy,
    "Principal Repaid (₹ Cr)": r.principal,
    "Interest Paid (₹ Cr)": r.interest,
  }));

  // Average coupon rate currently being paid on outstanding SDLs
  const avgCoupon = stack?.aggregates_for_state.weighted_average_coupon ?? null;
  const totalOutstanding = stack?.aggregates_for_state.total_outstanding_inr_crore ?? null;

  // Largest single-year repayments
  const sortedBySize = [...schedule].sort((a, b) => b.principal_due - a.principal_due).slice(0, 10);
  const topRepayData = sortedBySize.map((d) => ({
    label: d.fiscal_year,
    "Principal Due (₹ Cr)": d.principal_due,
  }));

  return (
    <div className="space-y-8">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Debt Repayments</h1>
          <p className="mt-1 text-slate-500">
            State Development Loan (SDL) maturity schedule — principal repayments by fiscal year
          </p>
          <LastUpdated timestamp={now} className="mt-1" />
        </div>
        <span className="inline-flex items-center rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
          Source: RBI Outstanding Securities
        </span>
      </div>

      {/* ── KPI Cards ─────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total SDL Outstanding"
          value={fmtLakhCrore(total)}
          description="Total principal to be repaid (all maturities)"
          lastUpdated={now}
        />
        <MetricCard
          title="Near-Term (5 yr)"
          value={fmtLakhCrore(nearTermTotal)}
          description="Due by FY 2029–30"
          lastUpdated={now}
        />
        <MetricCard
          title="Avg Interest Rate"
          value={avgCoupon !== null ? avgCoupon.toFixed(2) + "%" : "—"}
          description={
            totalOutstanding !== null
              ? "Weighted by outstanding principal (" + fmtLakhCrore(totalOutstanding) + ")"
              : "Weighted-average coupon on outstanding SDLs"
          }
          lastUpdated={now}
        />
        <MetricCard
          title="Peak Repayment Year"
          value={sortedBySize[0]?.fiscal_year ?? "—"}
          description={sortedBySize[0] ? fmtCrore(sortedBySize[0].principal_due) + " due" : ""}
          lastUpdated={now}
        />
      </div>

      {/* ── Annual Debt Service: Principal + Interest ─────────────── */}
      {debtServiceRows.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <h2 className="mb-1 text-base font-semibold text-slate-800">
            Annual Debt Service — Principal + Interest
          </h2>
          <p className="mb-5 text-xs text-slate-500">
            Total loan repayment and interest paid on total outstanding debt, by fiscal year
          </p>
          <BarChartClient
            data={debtServiceChartData}
            dataKey="Principal Repaid (₹ Cr)"
            dataKey2="Interest Paid (₹ Cr)"
            color="#0ea5a4"
            color2="#f59e0b"
            height={320}
          />
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-sm text-slate-600">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-2 pr-6 text-left font-semibold text-slate-700">Fiscal Year</th>
                  <th className="py-2 pr-6 text-right font-semibold text-slate-700">
                    Principal Repaid
                  </th>
                  <th className="py-2 pr-6 text-right font-semibold text-slate-700">
                    Interest Paid
                  </th>
                  <th className="py-2 text-right font-semibold text-slate-700">
                    Total Debt Service
                  </th>
                </tr>
              </thead>
              <tbody>
                {debtServiceRows.map((r) => (
                  <tr key={r.fy} className="border-b border-slate-50 hover:bg-slate-50/60">
                    <td className="py-2 pr-6 font-medium">{r.fy}</td>
                    <td className="py-2 pr-6 text-right">{fmtCrore(r.principal)}</td>
                    <td className="py-2 pr-6 text-right">{fmtCrore(r.interest)}</td>
                    <td className="py-2 text-right font-semibold text-slate-800">
                      {fmtCrore(r.total)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-slate-200 font-semibold bg-slate-50">
                  <td className="py-2 pr-6">Total</td>
                  <td className="py-2 pr-6 text-right">
                    {fmtCrore(debtServiceRows.reduce((s, r) => s + r.principal, 0))}
                  </td>
                  <td className="py-2 pr-6 text-right">
                    {fmtCrore(debtServiceRows.reduce((s, r) => s + r.interest, 0))}
                  </td>
                  <td className="py-2 text-right">
                    {fmtCrore(debtServiceRows.reduce((s, r) => s + r.total, 0))}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
          <p className="mt-4 text-xs text-slate-500">
            Principal: market borrowing repayments (AP Budget). Interest: gross interest on total
            outstanding debt (RBI State Finances).
            {avgCoupon !== null && (
              <>
                {" "}Current weighted-average interest rate on outstanding SDLs:{" "}
                <span className="font-semibold text-slate-700">{avgCoupon.toFixed(2)}%</span>.
              </>
            )}
          </p>
        </div>
      )}

      {/* ── Annual Maturity Schedule ───────────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">
          Annual SDL Principal Maturities (FY 2024–25 to 2050+)
        </h2>
        <p className="mb-5 text-xs text-slate-500">
          Principal repayments due each fiscal year from currently outstanding state development loans
        </p>
        <BarChartClient
          data={scheduleBarData}
          dataKey="Principal Due (₹ Cr)"
          color="#f59e0b"
          height={340}
        />
      </div>

      {/* ── Cumulative Repayment ───────────────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">
          Cumulative Repayment Trajectory
        </h2>
        <p className="mb-5 text-xs text-slate-500">
          How total SDL repayments accumulate year by year
        </p>
        <AreaChartClient
          data={cumulativeData}
          seriesKeys={["Cumulative (₹ Cr)", "Annual Due (₹ Cr)"]}
          colors={["#6366f1", "#f59e0b"]}
          yLabel="₹ Crore"
          height={320}
        />
      </div>

      {/* ── Top 10 repayment years ─────────────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-slate-800">
          Largest Repayment Years
        </h2>
        <p className="mb-5 text-xs text-slate-500">Top 10 fiscal years by SDL principal maturity</p>
        <BarChartClient
          data={topRepayData}
          dataKey="Principal Due (₹ Cr)"
          color="#f43f5e"
          height={280}
          horizontal
        />
      </div>

      {/* ── Full Schedule Table ───────────────────────────────────── */}
      <div className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-slate-800">Full Maturity Schedule</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-slate-600">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="py-2 pr-6 text-left font-semibold text-slate-700">Fiscal Year</th>
                <th className="py-2 pr-6 text-right font-semibold text-slate-700">Principal Due</th>
                <th className="py-2 pr-6 text-right font-semibold text-slate-700">Instruments</th>
                <th className="py-2 text-right font-semibold text-slate-700">% of Total</th>
              </tr>
            </thead>
            <tbody>
              {schedule.map((row) => (
                <tr key={row.fiscal_year} className="border-b border-slate-50 hover:bg-slate-50/60">
                  <td className="py-2 pr-6 font-medium">{row.fiscal_year}</td>
                  <td className="py-2 pr-6 text-right">{fmtCrore(row.principal_due)}</td>
                  <td className="py-2 pr-6 text-right">{row.instrument_count}</td>
                  <td className="py-2 text-right text-slate-500">
                    {total > 0 ? ((row.principal_due / total) * 100).toFixed(1) + "%" : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-200 font-semibold bg-slate-50">
                <td className="py-2 pr-6">Total</td>
                <td className="py-2 pr-6 text-right">{fmtLakhCrore(total)}</td>
                <td className="py-2 pr-6 text-right">
                  {schedule.reduce((s, d) => s + d.instrument_count, 0)}
                </td>
                <td className="py-2 text-right">100%</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* ── Data Notes ────────────────────────────────────────────── */}
      <div className="rounded-xl bg-slate-50 border border-slate-200 px-5 py-4 text-xs text-slate-500 space-y-1">
        <p className="font-semibold text-slate-600">Data Sources &amp; Notes</p>
        <p>• SDL maturity schedule derived from RBI Outstanding Securities data (current as of May 2026).</p>
        <p>• Each row represents aggregate principal maturing in that fiscal year (April–March).</p>
        <p>• Market borrowing repayments (budget side) from AP Budget Documents, FY 2023–24 to 2025–26.</p>
        <p>• Small pre-2020 entries represent residual instruments with very small outstanding balances.</p>
      </div>
    </div>
  );
}
