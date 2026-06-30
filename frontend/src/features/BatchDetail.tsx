import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Loader2, Upload } from "lucide-react";

import {
  getBatch,
  getBatchProgress,
  listDocuments,
  uploadDocument,
} from "../api/client";
import type { Batch, BatchProgress, Document } from "../types/api";

type BatchDetailProps = {
  apiKey: string;
  batchId: string;
  onBack: () => void;
  onOpenDocument: (documentId: string) => void;
};

export function BatchDetail({
  apiKey,
  batchId,
  onBack,
  onOpenDocument,
}: BatchDetailProps) {
  const [batch, setBatch] = useState<Batch | null>(null);
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceReference, setSourceReference] = useState("frontend-upload");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const batchDocuments = useMemo(() => {
    return documents.filter((document) => document.batch_id === batchId);
  }, [documents, batchId]);

  async function loadBatchDetail() {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [batchResponse, progressResponse, documentsResponse] =
        await Promise.all([
          getBatch(apiKey, batchId),
          getBatchProgress(apiKey, batchId),
          listDocuments(apiKey),
        ]);

      setBatch(batchResponse);
      setProgress(progressResponse);
      setDocuments(documentsResponse.items);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not load batch detail",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();

    if (!selectedFile) return;

    setIsUploading(true);
    setErrorMessage(null);

    try {
      await uploadDocument(apiKey, batchId, selectedFile, sourceReference);
      setSelectedFile(null);
      await loadBatchDetail();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not upload document",
      );
    } finally {
      setIsUploading(false);
    }
  }

  useEffect(() => {
    void loadBatchDetail();

    const intervalId = window.setInterval(() => {
      void loadBatchDetail();
    }, 4000);

    return () => window.clearInterval(intervalId);
  }, [apiKey, batchId]);

  return (
    <div className="dashboard">
      <header className="page-header">
        <div>
          <button className="ghost-button" onClick={onBack}>
            <ArrowLeft size={16} />
            Volver
          </button>
          <h1>{batch?.name ?? "Batch"}</h1>
          <p>{batch?.id}</p>
        </div>

        <button className="secondary-button" onClick={loadBatchDetail}>
          {isLoading ? <Loader2 className="spin" size={16} /> : "Actualizar"}
        </button>
      </header>

      {errorMessage && <div className="alert">{errorMessage}</div>}

      <section className="progress-panel">
        <div className="progress-header">
          <div>
            <strong>Progreso</strong>
            <span>{progress?.status ?? batch?.status ?? "unknown"}</span>
          </div>
          <strong>{progress?.progress_percent ?? 0}%</strong>
        </div>

        <div className="progress-track">
          <div
            className="progress-fill"
            style={{ width: `${progress?.progress_percent ?? 0}%` }}
          />
        </div>

        <div className="status-counts">
          {Object.entries(progress?.counts_by_status ?? {}).map(
            ([status, count]) => (
              <span key={status}>
                {status}: {count}
              </span>
            ),
          )}
        </div>
      </section>

      <section className="upload-panel">
        <form onSubmit={handleUpload}>
          <label>
            Archivo
            <input
              type="file"
              accept=".txt,.pdf,.png,.jpg,.jpeg"
              onChange={(event) =>
                setSelectedFile(event.target.files?.[0] ?? null)
              }
            />
          </label>

          <label>
            Source reference
            <input
              value={sourceReference}
              onChange={(event) => setSourceReference(event.target.value)}
            />
          </label>

          <button type="submit" disabled={!selectedFile || isUploading}>
            <Upload size={16} />
            {isUploading ? "Subiendo..." : "Subir documento"}
          </button>
        </form>
      </section>

      <section className="table-panel">
        {batchDocuments.length === 0 ? (
          <div className="empty-state compact">
            <p>Este batch todavía no tiene documentos.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Archivo</th>
                <th>Estado</th>
                <th>Tipo</th>
                <th>Confianza</th>
                <th>Duplicado</th>
              </tr>
            </thead>
            <tbody>
              {batchDocuments.map((document) => (
                <tr
                  key={document.id}
                  className="clickable-row"
                  onClick={() => onOpenDocument(document.id)}
                >
                  <td>
                    <strong>{document.filename}</strong>
                    <span>{document.id}</span>
                  </td>
                  <td>
                    <span className={`status-pill ${document.status}`}>
                      {document.status}
                    </span>
                  </td>
                  <td>{document.document_type ?? "-"}</td>
                  <td>
                    {document.confidence_score === null
                      ? "-"
                      : document.confidence_score}
                  </td>
                  <td>{document.is_duplicate_candidate ? "Sí" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}