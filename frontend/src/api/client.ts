import type {
  Batch,
  BatchListResponse,
  BatchProgress,
  Document,
  DocumentListResponse,
  Metrics,
  DocumentDetail,
  DocumentEvent,
  DocumentReviewResponse,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

type RequestOptions = {
  apiKey: string;
  method?: string;
  body?: unknown;
};

async function apiRequest<T>(
  path: string,
  { apiKey, method = "GET", body }: RequestOptions,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function listBatches(apiKey: string, status?: string) {
  const query = status ? `?status=${status}` : "";

  return apiRequest<BatchListResponse>(`/batches${query}`, {
    apiKey,
  });
}

export function getMetrics(apiKey: string) {
  return apiRequest<Metrics>("/metrics", {
    apiKey,
  });
}

export function createBatch(
  apiKey: string,
  payload: {
    name: string;
    source: string;
    metadata: Record<string, unknown>;
  },
) {
  return apiRequest("/batches", {
    apiKey,
    method: "POST",
    body: payload,
  });
}

export function getBatch(apiKey: string, batchId: string) {
  return apiRequest<Batch>(`/batches/${batchId}`, {
    apiKey,
  });
}

export function getBatchProgress(apiKey: string, batchId: string) {
  return apiRequest<BatchProgress>(`/batches/${batchId}/progress`, {
    apiKey,
  });
}

export function listDocuments(apiKey: string) {
  return apiRequest<DocumentListResponse>("/documents?limit=100", {
    apiKey,
  });
}

export async function uploadDocument(
  apiKey: string,
  batchId: string,
  file: File,
  sourceReference: string,
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("source_reference", sourceReference);

  const response = await fetch(`${API_BASE_URL}/batches/${batchId}/documents`, {
    method: "POST",
    headers: {
      "X-API-Key": apiKey,
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Upload failed with ${response.status}`);
  }

  return response.json() as Promise<Document>;
}

export function getDocument(apiKey: string, documentId: string) {
  return apiRequest<DocumentDetail>(`/documents/${documentId}`, {
    apiKey,
  });
}

export function getDocumentEvents(apiKey: string, documentId: string) {
  return apiRequest<DocumentEvent[]>(`/documents/${documentId}/events`, {
    apiKey,
  });
}

export function updateDocumentFields(
  apiKey: string,
  documentId: string,
  payload: {
    fields: Record<string, string>;
    reviewer_id: string;
  },
) {
  return apiRequest<DocumentReviewResponse>(`/documents/${documentId}/fields`, {
    apiKey,
    method: "PATCH",
    body: payload,
  });
}

export function approveDocument(
  apiKey: string,
  documentId: string,
  reviewerId: string,
) {
  return apiRequest<DocumentReviewResponse>(`/documents/${documentId}/approve`, {
    apiKey,
    method: "POST",
    body: {
      reviewer_id: reviewerId,
    },
  });
}

export function rejectDocument(
  apiKey: string,
  documentId: string,
  reviewerId: string,
  reason: string,
) {
  return apiRequest<DocumentReviewResponse>(`/documents/${documentId}/reject`, {
    apiKey,
    method: "POST",
    body: {
      reviewer_id: reviewerId,
      reason,
    },
  });
}

export function retryDocument(
  apiKey: string,
  documentId: string,
  reviewerId: string,
) {
  return apiRequest<DocumentReviewResponse>(`/documents/${documentId}/retry`, {
    apiKey,
    method: "POST",
    body: {
      reviewer_id: reviewerId,
    },
  });
}
