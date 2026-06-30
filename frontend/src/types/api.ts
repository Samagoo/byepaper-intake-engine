export type BatchStatus =
  | "created"
  | "receiving"
  | "processing"
  | "completed"
  | "failed"
  | "partially_failed";

export type DocumentStatus =
  | "uploaded"
  | "queued"
  | "extracting"
  | "classified"
  | "needs_review"
  | "approved"
  | "rejected"
  | "failed";

export type DocumentType =
  | "invoice"
  | "contract"
  | "id_document"
  | "bank_statement"
  | "other";

export type Batch = {
  id: string;
  organization_id: string;
  name: string;
  source: string;
  status: BatchStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BatchListResponse = {
  items: Batch[];
  total: number;
  limit: number;
  offset: number;
};

export type Metrics = {
  documents_total: number;
  documents_by_status: Record<string, number>;
  batches_total: number;
  batches_by_status: Record<string, number>;
  duplicate_candidates: number;
};