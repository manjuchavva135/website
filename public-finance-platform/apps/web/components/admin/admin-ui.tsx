import React from "react";
import type { ReviewQueueItem } from "@/lib/admin-api";

export function StatusPill({ status }: { status: string }) {
  const tone =
    status === "approved" || status === "published"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : status === "rejected"
        ? "border-red-200 bg-red-50 text-red-700"
        : status === "in_review"
          ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-slate-200 bg-slate-50 text-slate-700";

  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${tone}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function AdminCard({
  title,
  eyebrow,
  children,
  action,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white/90 p-5 shadow-sm shadow-slate-200/50">
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          {eyebrow && (
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-teal-700">{eyebrow}</p>
          )}
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function AdminEmpty({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 px-6 py-10 text-center">
      <h3 className="font-semibold text-slate-800">{title}</h3>
      <p className="mt-2 text-sm text-slate-500">{message}</p>
    </div>
  );
}

export function AdminError({ message }: { message: string }) {
  return (
    <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {message}
    </div>
  );
}

export function AdminSuccess({ message }: { message: string }) {
  return (
    <div role="status" className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
      {message}
    </div>
  );
}

export function QueueStats({ documents }: { documents: ReviewQueueItem[] }) {
  const pending = documents.filter((item) => ["pending", "new", "in_review"].includes(item.review_status)).length;
  const approved = documents.filter((item) => item.review_status === "approved").length;
  const rejected = documents.filter((item) => item.review_status === "rejected").length;
  const stats = [
    ["Documents", documents.length],
    ["Awaiting review", pending],
    ["Approved", approved],
    ["Rejected", rejected],
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map(([label, value]) => (
        <div key={label} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{value}</p>
        </div>
      ))}
    </div>
  );
}
