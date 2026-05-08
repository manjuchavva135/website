"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useRef, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { useAdminAuth } from "./admin-auth";
import { AdminCard, AdminError } from "./admin-ui";

const SOURCE_FAMILIES = [
  {
    value: "rbi_auction",
    label: "RBI SDL auction",
    hint: "Auction notification or result PDF (RBI press release).",
  },
  {
    value: "outstanding_securities",
    label: "Outstanding state securities",
    hint: "RBI's authoritative outstanding-debt PDF (OUTSTANDINGSGSDATA…).",
  },
  {
    value: "ap_budget",
    label: "AP Budget volume",
    hint: "Andhra Pradesh budget volume PDF (e.g. 2024-25 Vol-I).",
  },
  {
    value: "other",
    label: "Other",
    hint: "Generic document — parser will only extract raw pages.",
  },
] as const;

type UploadState =
  | { type: "idle" }
  | { type: "uploading" }
  | { type: "duplicate"; documentId: number }
  | { type: "error"; message: string };

export function AdminUploadView() {
  const { credentials } = useAdminAuth();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [sourceFamily, setSourceFamily] = useState<string>("rbi_auction");
  const [sourceName, setSourceName] = useState("");
  const [publicationDate, setPublicationDate] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [state, setState] = useState<UploadState>({ type: "idle" });

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    setState({ type: "uploading" });

    try {
      const result = await adminApi.uploadDocument(credentials, {
        file,
        source_family: sourceFamily,
        source_name: sourceName.trim(),
        publication_date: publicationDate || undefined,
        source_url: sourceUrl.trim() || undefined,
        notes: notes.trim() || undefined,
      });

      if (result.duplicate) {
        setState({ type: "duplicate", documentId: result.document_id });
        return;
      }

      router.push(`/admin/documents/${result.document_id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setState({ type: "error", message });
    }
  }

  const busy = state.type === "uploading";

  return (
    <AdminCard eyebrow="Manual ingestion" title="Upload document">
      {state.type === "duplicate" && (
        <div className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          This file was already uploaded.{" "}
          <Link
            href={`/admin/documents/${state.documentId}`}
            className="font-semibold underline underline-offset-2 hover:text-amber-900"
          >
            View existing document #{state.documentId}
          </Link>
        </div>
      )}

      {state.type === "error" && <AdminError message={state.message} />}

      <form className="mt-2 space-y-5" onSubmit={handleSubmit}>
        {/* File picker */}
        <div>
          <label className="block text-sm font-semibold text-slate-700">
            Document file
            <span className="ml-1 font-normal text-slate-400">.pdf, .html, .xlsx, .csv</span>
          </label>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.html,.xlsx,.csv,.xls"
            required
            disabled={busy}
            className="mt-2 block w-full cursor-pointer rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 file:mr-3 file:cursor-pointer file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-1 file:text-sm file:font-semibold hover:file:bg-slate-200 disabled:opacity-50"
          />
        </div>

        {/* Source family */}
        <div>
          <label className="block text-sm font-semibold text-slate-700">
            Source family
          </label>
          <select
            value={sourceFamily}
            onChange={(e) => setSourceFamily(e.target.value)}
            required
            disabled={busy}
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:opacity-50"
          >
            {SOURCE_FAMILIES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <p className="mt-1.5 text-xs text-slate-500">
            {SOURCE_FAMILIES.find((f) => f.value === sourceFamily)?.hint}
          </p>
        </div>

        {/* Source name */}
        <div>
          <label className="block text-sm font-semibold text-slate-700">
            Source name
            <span className="ml-1 font-normal text-slate-400">e.g. "RBI SDL Auction Apr 2024"</span>
          </label>
          <input
            type="text"
            value={sourceName}
            onChange={(e) => setSourceName(e.target.value)}
            required
            disabled={busy}
            placeholder="RBI SDL Auction Apr 2024"
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:opacity-50"
          />
        </div>

        {/* Optional fields row */}
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-semibold text-slate-700">
              Publication date
              <span className="ml-1 font-normal text-slate-400">optional</span>
            </label>
            <input
              type="date"
              value={publicationDate}
              onChange={(e) => setPublicationDate(e.target.value)}
              disabled={busy}
              className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:opacity-50"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700">
              Source URL
              <span className="ml-1 font-normal text-slate-400">optional</span>
            </label>
            <input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              disabled={busy}
              placeholder="https://rbi.org.in/..."
              className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:opacity-50"
            />
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-semibold text-slate-700">
            Notes
            <span className="ml-1 font-normal text-slate-400">optional</span>
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={busy}
            rows={3}
            placeholder="Any context about this document..."
            className="mt-2 w-full resize-none rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:opacity-50"
          />
        </div>

        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-slate-950 px-6 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
        >
          {busy ? "Uploading…" : "Upload and parse"}
        </button>
      </form>
    </AdminCard>
  );
}
