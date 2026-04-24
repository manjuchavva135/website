import type { ChangelogEntry } from "@public-finance/shared-ts";

async function getChangelog(): Promise<ChangelogEntry[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/api/v1/changelog`, { cache: "no-store" });
  if (!response.ok) return [];
  return (await response.json()) as ChangelogEntry[];
}

export default async function ChangelogPage() {
  const changelog = await getChangelog();

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-4xl font-semibold tracking-tight">Changelog</h1>
      <div className="mt-8 space-y-4">
        {changelog.map((entry) => (
          <article key={`${entry.version}-${entry.created_at}`} className="rounded-xl border border-slate-200 bg-white p-5">
            <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">{entry.version}</p>
            <h2 className="mt-1 text-xl font-medium">{entry.title}</h2>
            <p className="mt-2 text-slate-700">{entry.details}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
