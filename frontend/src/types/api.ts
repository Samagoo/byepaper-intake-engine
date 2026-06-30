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

export type Document = {
  id: string;
  organization_id: string;
  batch_id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  checksum_sha256: string;
  status: DocumentStatus;
  document_type: DocumentType | null;
  confidence_score: number | null;
  storage_key: string;
  source_reference: string | null;
  uploaded_at: string;
  is_duplicate_candidate: boolean;
  duplicate_of_document_id: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentListResponse = {
  items: Document[];
  total: number;
  limit: number;
  offset: number;
};

export type BatchProgress = {
  batch_id: string;
  status: BatchStatus;
  total_documents: number;
  counts_by_status: Record<string, number>;
  progress_percent: number;
};

export type ExtractedField = {
  id: string;
  key_field: string;
  value: string;
  confidence_score: number | null;
  created_at: string;
};

export type ValidationError = {
  id: string;
  field_name: string;
  error_message: string;
  created_at: string;
};

export type DocumentEvent = {
  id: string;
  organization_id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor_type: string;
  actor_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type DocumentDetail = Document & {
  extracted_fields?: ExtractedField[];
  validation_errors?: ValidationError[];
};

export type DocumentReviewResponse = {
  document_id: string;
  status: string;
  updated_fields?: string[];
  missing_fields?: string[];
  reason?: string;
};