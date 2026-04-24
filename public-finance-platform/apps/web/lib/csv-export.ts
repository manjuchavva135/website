/** Client-side CSV export utilities. Only call from client components. */

function escapeCell(value: string): string {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export function rowsToCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  // Exclude internal _provenance arrays
  const cols = Object.keys(rows[0]).filter((k) => !k.startsWith("_"));
  const header = cols.map(escapeCell).join(",");
  const body = rows.map((row) =>
    cols.map((c) => escapeCell(String(row[c] ?? ""))).join(",")
  );
  return [header, ...body].join("\r\n");
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[]): void {
  const csv = rowsToCsv(rows);
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
