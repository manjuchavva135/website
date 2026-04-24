"use client";

import React from "react";
import { useCallback, useEffect, useState } from "react";
import { adminApi, type ReleaseRecord } from "@/lib/admin-api";
import { useAdminAuth } from "./admin-auth";
import { AdminCard, AdminEmpty, AdminError, AdminSuccess, StatusPill } from "./admin-ui";

const DEFAULT_DATASET = "andhra_public_finance";

export function AdminReleaseWorkspace() {
  const { credentials } = useAdminAuth();
  const [history, setHistory] = useState<ReleaseRecord[]>([]);
  const [datasetName, setDatasetName] = useState(DEFAULT_DATASET);
  const [version, setVersion] = useState(`v${new Date().toISOString().slice(0, 10).replaceAll("-", ".")}`);
  const [releaseNotes, setReleaseNotes] = useState("");
  const [changelogTitle, setChangelogTitle] = useState("Dataset release");
  const [changelogDetails, setChangelogDetails] = useState("");
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setHistory(await adminApi.releaseHistory(credentials, datasetName));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load release history");
    } finally {
      setLoading(false);
    }
  }, [credentials, datasetName]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const manifestPreview = {
    dataset_name: datasetName,
    release_version: version,
    generated_by: credentials.email,
    release_notes: releaseNotes || "(pending)",
    changelog: {
      title: changelogTitle || "(pending)",
      details: changelogDetails || "(pending)",
    },
    rules: [
      "Only approved/rejected facts are eligible for release.",
      "Pending documents and facts block publication.",
      "Release records are immutable after publication.",
    ],
  };

  async function publish(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPublishing(true);
    setError(null);
    setSuccess(null);
    try {
      const release = await adminApi.publishRelease(credentials, {
        dataset_name: datasetName,
        release_version: version,
        release_notes: releaseNotes,
        changelog_title: changelogTitle,
        changelog_details: changelogDetails,
      });
      setSuccess(`Release ${release.release_version} published with manifest ${release.manifest_checksum_sha256}.`);
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to publish release");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-teal-700">Release workflow</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950">Publish dataset release</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Create an immutable release record, manifest metadata, and changelog entry after admin review is complete.
        </p>
      </div>

      {error && <AdminError message={error} />}
      {success && <AdminSuccess message={success} />}

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <AdminCard title="Release details" eyebrow="Publish">
          <form className="space-y-4" onSubmit={publish}>
            <label className="block text-sm font-semibold text-slate-700">
              Dataset name
              <input
                className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
                required
                value={datasetName}
                onChange={(event) => setDatasetName(event.target.value)}
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Release version
              <input
                className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
                required
                value={version}
                onChange={(event) => setVersion(event.target.value)}
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Release notes
              <textarea
                className="mt-2 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
                required
                value={releaseNotes}
                onChange={(event) => setReleaseNotes(event.target.value)}
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Changelog title
              <input
                className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
                required
                value={changelogTitle}
                onChange={(event) => setChangelogTitle(event.target.value)}
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Changelog details
              <textarea
                className="mt-2 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
                required
                value={changelogDetails}
                onChange={(event) => setChangelogDetails(event.target.value)}
              />
            </label>
            <button
              className="w-full rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
              disabled={publishing}
            >
              {publishing ? "Publishing..." : "Publish immutable release"}
            </button>
          </form>
        </AdminCard>

        <AdminCard title="Manifest and changelog preview" eyebrow="Preview">
          <pre className="max-h-[32rem] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs leading-6 text-teal-50">
            {JSON.stringify(manifestPreview, null, 2)}
          </pre>
        </AdminCard>
      </div>

      <AdminCard title="Release history" eyebrow="Immutable">
        {loading ? (
          <div className="h-40 animate-pulse rounded-2xl bg-slate-100" role="status" aria-label="Loading release history" />
        ) : history.length === 0 ? (
          <AdminEmpty title="No releases yet" message="Publish the first approved dataset release to populate history." />
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="p-3">Version</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Manifest</th>
                  <th className="p-3">Published</th>
                </tr>
              </thead>
              <tbody>
                {history.map((release) => (
                  <tr key={release.id} className="border-t border-slate-100 align-top">
                    <td className="p-3">
                      <p className="font-semibold">{release.release_version}</p>
                      <p className="mt-1 text-xs text-slate-500">{release.release_notes}</p>
                    </td>
                    <td className="p-3">
                      <StatusPill status={release.status} />
                    </td>
                    <td className="p-3 font-mono text-xs text-slate-600">
                      <p>{release.manifest_checksum_sha256 ?? "n/a"}</p>
                      <p className="mt-1">{release.manifest_storage_key ?? "n/a"}</p>
                    </td>
                    <td className="p-3">{release.published_at ?? release.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AdminCard>
    </div>
  );
}
