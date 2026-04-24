export type ApiHealthResponse = {
  service: "api";
  status: "ok";
  environment: string;
};

export type MetricSeries = {
  slug: string;
  title: string;
  metric_group: string;
  unit: string;
  description: string;
};

export type MetricObservation = {
  id: number;
  series_slug: string;
  period_start: string;
  period_end: string;
  period_label: string;
  amount: string;
  currency: string;
  basis: string;
  source_document_id: number;
  source_row_id: number | null;
  provenance_note: string | null;
};

export type ReviewQueueItem = {
  document_id: number;
  source_name: string;
  title: string;
  parser_version: string;
  review_status: "pending" | "approved" | "rejected";
  checksum_sha256: string;
  created_at: string;
};

export type ChangelogEntry = {
  version: string;
  title: string;
  details: string;
  created_at: string;
};
