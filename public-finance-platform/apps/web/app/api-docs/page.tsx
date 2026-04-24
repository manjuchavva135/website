import type { Metadata } from "next";
import { apiBaseUrl, buildApiServiceUrl, buildApiUrl } from "@/lib/api-url";

export const metadata: Metadata = { title: "API Documentation" };

const ENDPOINTS = [
  {
    group: "Health",
    items: [
      { method: "GET", path: "/api/v1/health", description: "API liveness check. Returns service name, status, and environment." },
    ],
  },
  {
    group: "Metrics",
    items: [
      { method: "GET", path: "/api/v1/metrics", description: "List all published metric series." },
      { method: "GET", path: "/api/v1/metrics/{slug}/observations", description: "Paginated observations for a metric series. Supports ?limit=." },
      { method: "GET", path: "/api/v1/metrics/{slug}/observations.csv", description: "Download observations as CSV." },
    ],
  },
  {
    group: "Debt",
    items: [
      { method: "GET", path: "/api/v1/debt/outstanding", description: "Outstanding debt stock with provenance. Filters: financial_year, basis, as_of, start_date, end_date, page, page_size, sort_by, sort_order, format." },
      { method: "GET", path: "/api/v1/debt/issues", description: "Confirmed debt issuances. Same filters as outstanding." },
      { method: "GET", path: "/api/v1/debt/pipeline", description: "Scheduled (not yet settled) debt events." },
      { method: "GET", path: "/api/v1/debt/repayments", description: "Principal and coupon repayment events." },
    ],
  },
  {
    group: "Fiscal",
    items: [
      { method: "GET", path: "/api/v1/fiscal/receipts", description: "Revenue and capital receipts. Filters: financial_year, basis, period_type, department, start_date, end_date." },
      { method: "GET", path: "/api/v1/fiscal/expenditure", description: "Government expenditure by head." },
      { method: "GET", path: "/api/v1/fiscal/deficits", description: "Fiscal, revenue and primary deficit series." },
    ],
  },
  {
    group: "Departments",
    items: [
      { method: "GET", path: "/api/v1/departments/spending", description: "Department-level sanctioned vs actual spending." },
    ],
  },
  {
    group: "Reference",
    items: [
      { method: "GET", path: "/api/v1/sources", description: "Catalog of all ingested source documents." },
      { method: "GET", path: "/api/v1/releases", description: "Dataset release log." },
      { method: "GET", path: "/api/v1/changelog", description: "Platform changelog entries." },
      { method: "GET", path: "/api/v1/provenance/{observation_id}", description: "Full provenance chain for a single observation." },
    ],
  },
];

const COMMON_PARAMS = [
  { name: "financial_year", type: "string", example: "2024-25", description: "Filter by financial year label." },
  { name: "basis", type: "string", example: "audited_actual", description: "One of: audited_actual, monthly_actual_provisional, budget_estimate, revised_estimate, projection, scheduled, notified, issued, due, paid." },
  { name: "period_type", type: "string", example: "annual", description: "One of: annual, half_year, quarter, month." },
  { name: "department", type: "string", example: "Finance", description: "Department name substring match." },
  { name: "start_date", type: "date", example: "2024-04-01", description: "ISO 8601 date." },
  { name: "end_date", type: "date", example: "2025-03-31", description: "ISO 8601 date." },
  { name: "as_of", type: "date", example: "2024-12-31", description: "Point-in-time for stock queries." },
  { name: "page", type: "integer", example: "1", description: "1-based page number." },
  { name: "page_size", type: "integer", example: "50", description: "Max 500 per page." },
  { name: "sort_by", type: "string", example: "period_start", description: "Field name to sort by." },
  { name: "sort_order", type: "string", example: "desc", description: "asc or desc." },
  { name: "format", type: "string", example: "json", description: "json (default) or csv." },
];

export default function ApiDocsPage() {
  const base = apiBaseUrl();

  return (
    <div className="max-w-3xl space-y-10">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-ink">API Documentation</h1>
        <p className="mt-2 text-slate-600">
          The AP Finance platform exposes a REST JSON API. All endpoints support a{" "}
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-sm">format=csv</code> query
          parameter for bulk downloads.
        </p>
      </div>

      {/* Interactive docs link */}
      <div className="rounded-xl border border-tide/30 bg-tide/5 p-5">
        <h2 className="font-semibold text-tide">Interactive API Explorer</h2>
        <p className="mt-1 text-sm text-slate-600">
          The full OpenAPI schema with Try-it-out is served directly by the backend.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <a
            href={buildApiServiceUrl("/docs")}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg bg-tide px-4 py-2 text-sm font-medium text-white hover:bg-teal-600"
          >
            Open Swagger UI →
          </a>
          <a
            href={buildApiServiceUrl("/redoc")}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-tide px-4 py-2 text-sm font-medium text-tide hover:bg-tide/10"
          >
            Open ReDoc →
          </a>
          <a
            href={buildApiServiceUrl("/openapi.json")}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            OpenAPI JSON ↓
          </a>
        </div>
      </div>

      {/* Base URL */}
      <section>
        <h2 className="text-xl font-semibold text-slate-800">Base URL</h2>
        <code className="mt-2 block rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
          {base}
        </code>
      </section>

      {/* Endpoints */}
      <section>
        <h2 className="text-xl font-semibold text-slate-800">Endpoints</h2>
        <div className="mt-4 space-y-6">
          {ENDPOINTS.map((group) => (
            <div key={group.group}>
              <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-400">
                {group.group}
              </h3>
              <div className="space-y-2">
                {group.items.map((item) => (
                  <div
                    key={item.path}
                    className="rounded-lg border border-slate-200 bg-white/80 px-4 py-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-700">
                        {item.method}
                      </span>
                      <code className="text-sm font-medium text-slate-800">{item.path}</code>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{item.description}</p>
                    <a
                      href={buildApiUrl(item.path.replace(/{[^}]+}/g, "1"))}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1.5 inline-block text-xs text-tide underline"
                    >
                      Try in browser →
                    </a>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Common query parameters */}
      <section>
        <h2 className="text-xl font-semibold text-slate-800">Common Query Parameters</h2>
        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 text-left">
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Parameter</th>
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Type</th>
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Example</th>
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {COMMON_PARAMS.map((p) => (
                <tr key={p.name} className="hover:bg-slate-50/60">
                  <td className="px-4 py-2.5 font-mono text-tide">{p.name}</td>
                  <td className="px-4 py-2.5 text-slate-500">{p.type}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-600">{p.example}</td>
                  <td className="px-4 py-2.5 text-slate-600">{p.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Example */}
      <section>
        <h2 className="text-xl font-semibold text-slate-800">Example Requests</h2>
        <div className="mt-4 space-y-4 text-sm">
          {[
            {
              label: "Get audited debt outstanding for 2024-25",
              code: `curl "${buildApiUrl("/api/v1/debt/outstanding", { financial_year: "2024-25", basis: "audited_actual", format: "json" })}"`,
            },
            {
              label: "Download all fiscal receipts as CSV",
              code: `curl "${buildApiUrl("/api/v1/fiscal/receipts", { format: "csv", page_size: 2000 })}" -o receipts.csv`,
            },
            {
              label: "Get provenance for observation #42",
              code: `curl "${buildApiUrl("/api/v1/provenance/42")}"`,
            },
          ].map((ex) => (
            <div key={ex.label} className="rounded-xl border border-slate-200 bg-slate-50">
              <p className="border-b border-slate-200 px-4 py-2 text-xs font-medium text-slate-500">
                {ex.label}
              </p>
              <pre className="overflow-x-auto px-4 py-3 font-mono text-xs text-slate-800">
                {ex.code}
              </pre>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
