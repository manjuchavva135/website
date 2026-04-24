"use client";

import { PageError } from "@/components/ui/page-error";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="space-y-4">
      <PageError message={error.message || "An unexpected error occurred while loading this page."} />
      <button
        onClick={reset}
        className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        Try again
      </button>
    </div>
  );
}