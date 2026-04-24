interface LastUpdatedProps {
  timestamp?: string | null;
  className?: string;
}

export function LastUpdated({ timestamp, className = "" }: LastUpdatedProps) {
  if (!timestamp) {
    return (
      <p className={`text-xs text-slate-400 ${className}`}>Last updated: unavailable</p>
    );
  }
  const d = new Date(timestamp);
  const formatted = d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  });
  const time = d.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
    hour12: false,
  });
  return (
    <p className={`text-xs text-slate-400 ${className}`} title={timestamp}>
      Last updated: {formatted} {time} IST
    </p>
  );
}
