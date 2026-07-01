import { useEffect, useState } from "react";
import { ArrowLeft, Check, RefreshCcw, Save, X } from "lucide-react";

import {
  approveDocument,
  getDocument,
  getDocumentEvents,
  rejectDocument,
  retryDocument,
  updateDocumentFields,
} from "../api/client";
import type { DocumentDetail as DocumentDetailType, DocumentEvent } from "../types/api";

const defaultFieldsByDocumentType: Record<string, Record<string, string>> = {
  invoice: {
    vendor: "",
    total: "",
    currency: "MXN",
    document_date: "",
  },
  contract: {
    contract_number: "",
    person_name: "",
    document_date: "",
  },
  id_document: {
    person_name: "",
    document_date: "",
  },
  bank_statement: {
    person_name: "",
    total: "",
    currency: "MXN",
    document_date: "",
  },
  other: {
    description: "",
  },
};

function buildEditableFields(document: DocumentDetailType) {
  const template =
    defaultFieldsByDocumentType[document.document_type ?? "other"] ?? {};

  const extractedFields = Object.fromEntries(
    (document.extracted_fields ?? []).map((field) => [
      field.key_field,
      field.value ?? "",
    ]),
  );

  return {
    ...template,
    ...extractedFields,
  };
}

function hasFilledField(fieldsText: string) {
  try {
    const fields = JSON.parse(fieldsText) as Record<string, unknown>;

    return Object.values(fields).some(
      (value) => String(value ?? "").trim().length > 0,
    );
  } catch {
    return false;
  }
}

type DocumentDetailProps = {
  apiKey: string;
  documentId: string;
  onBack: () => void;
};

export function DocumentDetail({
  apiKey,
  documentId,
  onBack,
}: DocumentDetailProps) {
  const [document, setDocument] = useState<DocumentDetailType | null>(null);
  const [events, setEvents] = useState<DocumentEvent[]>([]);
  const [fieldsText, setFieldsText] = useState("");
  const [reviewerId, setReviewerId] = useState("reviewer-demo");
  const [rejectReason, setRejectReason] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasAnyFilledField = hasFilledField(fieldsText);
  const canApprove =
  document?.status === "needs_review" && hasAnyFilledField;

  async function loadDocument() {
    setErrorMessage(null);

    try {
      const [documentResponse, eventResponse] = await Promise.all([
        getDocument(apiKey, documentId),
        getDocumentEvents(apiKey, documentId),
      ]);

      setDocument(documentResponse);
      setEvents(eventResponse);

      setFieldsText(JSON.stringify(buildEditableFields(documentResponse), null, 2));

    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not load document",
      );
    }
  }

  async function handleSaveFields() {
    try {
      const parsedFields = JSON.parse(fieldsText) as Record<string, string>;

      await updateDocumentFields(apiKey, documentId, {
        fields: parsedFields,
        reviewer_id: reviewerId,
      });

      await loadDocument();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not update fields",
      );
    }
  }

  async function handleApprove() {
  if (!hasAnyFilledField) {
    setErrorMessage(
      "Antes de aprobar, llena al menos un campo del documento.",
    );
    return;
  }

  await approveDocument(apiKey, documentId, reviewerId);
  await loadDocument();
}

  async function handleReject() {
    await rejectDocument(apiKey, documentId, reviewerId, rejectReason);
    await loadDocument();
  }

  async function handleRetry() {
    await retryDocument(apiKey, documentId, reviewerId);
    await loadDocument();
  }

  useEffect(() => {
    void loadDocument();
  }, [apiKey, documentId]);

  return (
    <div className="dashboard">
      <header className="page-header">
        <div>
          <button className="ghost-button" onClick={onBack}>
            <ArrowLeft size={16} />
            Volver
          </button>
          <h1>{document?.filename ?? "Documento"}</h1>
          <p>{documentId}</p>
        </div>
      </header>

      {errorMessage && <div className="alert">{errorMessage}</div>}

      <section className="detail-grid">
        <div className="detail-panel">
          <h2>Estado</h2>
          <span className={`status-pill ${document?.status}`}>
            {document?.status ?? "loading"}
          </span>
          <p>Tipo: {document?.document_type ?? "-"}</p>
          <p>Confianza: {document?.confidence_score ?? "-"}</p>
          <p>Duplicado: {document?.is_duplicate_candidate ? "Sí" : "No"}</p>
        </div>

        <div className="detail-panel">
          <h2>Revisor</h2>
          <input
            value={reviewerId}
            onChange={(event) => setReviewerId(event.target.value)}
          />
        </div>
      </section>

      <section className="detail-panel">
        <h2>Campos extraídos</h2>
        <textarea
          className="json-editor"
          value={fieldsText}
          onChange={(event) => setFieldsText(event.target.value)}
        />
        <button onClick={handleSaveFields}>
          <Save size={16} />
          Guardar campos
        </button>
      </section>

      {document?.validation_errors?.length ? (
        <div className="validation-list">
          {document.validation_errors.map((error) => (
            <span key={error.id}>
              {error.key_field}: {error.message}
            </span>
          ))}
        </div>
      ) : null}

      <section className="review-actions">
        <button onClick={handleApprove} disabled={!canApprove}>
          <Check size={16} />
          Aprobar
        </button>

        <input
          value={rejectReason}
          onChange={(event) => setRejectReason(event.target.value)}
          placeholder="Motivo de rechazo"
        />

        <button className="danger-button" onClick={handleReject}>
          <X size={16} />
          Rechazar
        </button>

        <button className="secondary-button" onClick={handleRetry}>
          <RefreshCcw size={16} />
          Reintentar
        </button>
      </section>

      <section className="detail-panel">
        <h2>Auditoría</h2>
        <div className="event-list">
          {events.map((event) => (
            <div key={event.id} className="event-item">
              <strong>{event.event_type}</strong>
              <span>{event.actor_type}</span>
              <code>{JSON.stringify(event.payload)}</code>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}