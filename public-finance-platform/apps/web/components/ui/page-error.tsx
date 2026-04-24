interface PageErrorProps {
  message?: string;
  retryHref?: string;
}

export function PageError({
  message = "Unable to reach the data API. The service may be starting up.",
  retryHref,
}: PageErrorProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-2xl border border-red-200 bg-red-50 px-6 py-12 text-center"
    >
      <span className="text-3xl" aria-hidden="true">
        ⚠️
      </span>
      <h3 className="mt-3 text-base font-semibold text-red-800">Data unavailable</h3>
      <p className="mt-2 max-w-sm text-sm text-red-700">{message}</p>
      {retryHref && (
        <a
          href={retryHref}
          className="mt-5 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
        >
          Retry
        </a>
      )}
    </div>
  );
}
