"use client";

import Link from "next/link";
import React from "react";
import { useCallback, useEffect, useState } from "react";
import { adminApi, type AdminDocumentDetail } from "@/lib/admin-api";
import { useAdminAuth } from "./admin-auth";
import { AdminCard, AdminEmpty, AdminError, AdminSuccess, StatusPill } from "./admin-ui";

export function AdminDocumentDetailView({ documentId }: { documentId: number }) {
  const { credentials } = useAdminAuth();
  const [document, setDocument] = useState<AdminDocumentDetail | null>(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setDocument(await adminApi.document(credentials, documentId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load document");
    }
  }, [credentials, documentId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function transition(toState: string) {
    setBusy(toState);
    setError(null);
    setSuccess(null);
    try {
      await adminApi.transitionDocument(credentials, documentId, toState, comment || undefined);
      setSuccess(`Document marked ${toState.replaceAll("_", " ")}.`);
      setComment("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update document state");
    } finally {
      setBusy(null);
    }
  }

  async function decideFact(targetTable: string, targetId: number, decision: "approve" | "reject") {
    setBusy(`${decision}-${targetTable}-${targetId}`);
    setError(null);
    setSuccess(null);
    try {
      await adminApi.decideFact(credentials, targetTable, targetId, decision, comment || undefined);
      setSuccess(`Fact ${targetTable}#${targetId} ${decision}d.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to review fact");
    } finally {
      setBusy(null);
    }
  }

  async function rerunParse() {
    setBusy("rerun");
    setError(null);
    setSuccess(null);
    try {
      const response = await adminApi.rerunParse(credentials, documentId);
      setSuccess(`Parser re-run requested. Parser run ${response.parser_run_id} is ${response.status}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request parser re-run");
    } finally {
      setBusy(null);
    }
  }

  if (!document && !error) {
    return (
      <div className="space-y-4" role="status" aria-label="Loading document detail">
        <div className="h-24 animate-pulse rounded-[2rem] bg-slate-200" />
        <div className="h-96 animate-pulse rounded-[2rem] bg-slate-100" />
      </div>
    );
  }

  if (!document) {
    return <AdminError message={error ?? "Document not found"} />;
  }

  const latestParserRun = document.parser_runs[0];
  const warningCount = document.parser_errors.filter((item) => item.error_level === "warning").length;

  return (
    <div className="space-y-6">
      <Link className="text-sm font-semibold text-teal-700 hover:text-teal-900" href="/admin/review-queue">
        Back to review queue
      </Link>
      <div className="rounded-[2rem] border border-slate-200 bg-white/90 p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.3em] text-teal-700">Document inspection</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{document.title}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-600">
              <span>{document.source_name}</span>
              <span className="text-slate-300">/</span>
              <span>Parser {document.parser_version ?? "n/a"}</span>
              <StatusPill status={document.review_status} />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              disabled={busy === "in_review"}
              onClick={() => void transition("in_review")}
            >
              Start review
            </button>
            <button
              className="rounded-full bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
              disabled={busy === "approved"}
              onClick={() => void transition("approved")}
            >
              Approve document
            </button>
            <button
              className="rounded-full bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800"
              disabled={busy === "rejected"}
              onClick={() => void transition("rejected")}
            >
              Reject document
            </button>
            <button
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
              disabled={busy === "rerun"}
              onClick={() => void rerunParse()}
            >
              Re-run parse
            </button>
          </div>
        </div>
        <label className="mt-5 block text-sm font-semibold text-slate-700">
          Review comment
          <textarea
            className="mt-2 min-h-20 w-full rounded-2xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
            placeholder="Add rationale for document or fact decision"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
        </label>
      </div>

      {error && <AdminError message={error} />}
      {success && <AdminSuccess message={success} />}

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <AdminCard title="Parser confidence and warnings" eyebrow="Quality signals">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Latest status</p>
              <p className="mt-2 font-semibold">{latestParserRun?.status ?? "No parser run"}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Rows extracted</p>
              <p className="mt-2 font-mono text-xl font-semibold">{latestParserRun?.rows_extracted ?? document.rows.length}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Warnings</p>
              <p className="mt-2 font-mono text-xl font-semibold">{latestParserRun?.warnings_count ?? warningCount}</p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {document.parser_errors.length === 0 ? (
              <AdminEmpty title="No parser warnings" message="This document has no recorded parser warnings or errors." />
            ) : (
              document.parser_errors.map((item) => (
                <div key={item.id} className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm">
                  <p className="font-semibold text-amber-900">
                    {item.error_level.toUpperCase()} {item.error_code ? `/ ${item.error_code}` : ""}
                  </p>
                  <p className="mt-1 text-amber-800">{item.message}</p>
                  <p className="mt-1 text-xs text-amber-700">
                    Row {item.row_number ?? "n/a"} Column {item.column_name ?? "n/a"} Raw {item.raw_value ?? "n/a"}
                  </p>
                </div>
              ))
            )}
          </div>
        </AdminCard>

        <AdminCard title="Extracted facts" eyebrow="Approval controls">
          {document.extracted_facts.length === 0 ? (
            <AdminEmpty title="No extracted facts" message="No canonical facts are linked to this source document yet." />
          ) : (
            <div className="space-y-3">
              {document.extracted_facts.map((fact) => (
                <article key={`${fact.target_table}-${fact.target_id}-${fact.row_number}`} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                    <div>
                      <p className="font-semibold text-slate-950">
                        {fact.target_table} #{fact.target_id}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        Page {fact.page_number ?? "n/a"}, row {fact.row_number ?? "n/a"} {fact.row_label ? `/ ${fact.row_label}` : ""}
                      </p>
                      <p className="mt-2 rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                        {fact.quoted_text ?? "No quoted source text captured."}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                      <StatusPill status={fact.review_status} />
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 font-mono text-xs text-slate-700">
                        Confidence {fact.confidence_score ?? "n/a"}
                      </span>
                      <div className="flex gap-2">
                        <button
                          className="rounded-full bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800"
                          disabled={busy === `approve-${fact.target_table}-${fact.target_id}`}
                          onClick={() => void decideFact(fact.target_table, fact.target_id, "approve")}
                        >
                          Approve
                        </button>
                        <button
                          className="rounded-full bg-red-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-800"
                          disabled={busy === `reject-${fact.target_table}-${fact.target_id}`}
                          onClick={() => void decideFact(fact.target_table, fact.target_id, "reject")}
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </AdminCard>
      </div>

      <AdminCard title="Extracted rows with source page provenance" eyebrow="Source rows">
        {document.rows.length === 0 ? (
          <AdminEmpty title="No rows extracted" message="This document has no extracted rows to inspect." />
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="p-3">Page</th>
                  <th className="p-3">Row</th>
                  <th className="p-3">Label</th>
                  <th className="p-3">Raw text</th>
                  <th className="p-3">Checksum</th>
                </tr>
              </thead>
              <tbody>
                {document.rows.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100 align-top">
                    <td className="p-3 font-mono">{row.page_number ?? "n/a"}</td>
                    <td className="p-3 font-mono">{row.row_number ?? "n/a"}</td>
                    <td className="p-3">{row.row_label ?? "Unlabelled"}</td>
                    <td className="max-w-xl p-3 text-slate-700">{row.raw_text}</td>
                    <td className="p-3 font-mono text-xs text-slate-500">{row.checksum_sha256.slice(0, 16)}...</td>
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
