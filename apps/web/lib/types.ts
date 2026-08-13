export type Original = {
  id: string;
  sha256: string;
  byte_size: number;
  page_count: number | null;
  detected_features: { warnings?: string[]; encrypted?: boolean; acroform?: boolean; signatures?: boolean };
  download_url: string;
};

export type Version = {
  id: string;
  version_number: number;
  sha256: string;
  byte_size: number;
  page_count: number;
  download_url: string;
};

export type Document = {
  id: string;
  display_name: string;
  media_type: string;
  state: "active" | "expired" | "deleted";
  created_at: string;
  expires_at: string | null;
  original: Original;
  latest_version: Version | null;
  versions?: Version[];
};

export type Job = {
  id: string;
  state: "queued" | "running" | "validating" | "succeeded" | "failed" | "cancelled";
  progress_percent: number;
  operation_id: string | null;
  result_ids: string[];
  result?: Record<string, unknown> | null;
  error: { code: string; message: string; recoverable: boolean } | null;
};

export type Preview = {
  id: string;
  page_number: number;
  width: number;
  height: number;
  content_url: string;
};

export type AuditEvent = {
  id: string;
  occurred_at: string;
  event_type: string;
  output_sha256: string | null;
  payload: Record<string, unknown>;
};

