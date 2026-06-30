import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    ActorType,
    DocumentStatus,
    DocumentType,
    FieldSource,
)


class ExtractedFieldRead(BaseModel):
    """
    Representa un campo extraido o corregido de un documento.

    Ejemplo:
    key_field = "total"
    value = "8500"
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    key_field: str
    value: str | None
    confidence_score: float | None
    source: FieldSource
    corrected_by: str | None = None
    corrected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DocumentValidationErrorRead(BaseModel):
    """
    Representa un error de validacion del documento.

    Ejemplo:
    Falta el campo vendor en una factura.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    key_field: str
    code: str
    message: str
    created_at: datetime
    resolved_at: datetime | None = None


class EventLogRead(BaseModel):
    """
    Representa un evento de auditoria.

    Sirve para reconstruir la historia del documento.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    event_type: str
    actor_type: ActorType
    actor_id: str | None = None
    payload: dict
    created_at: datetime


class DocumentRead(BaseModel):
    """
    Respuesta resumida de un documento.

    Se usa para listas y respuestas de upload.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    batch_id: uuid.UUID
    filename: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    status: DocumentStatus
    document_type: DocumentType | None = None
    confidence_score: float | None = None
    storage_key: str
    source_reference: str | None = None
    uploaded_at: datetime
    is_duplicate_candidate: bool
    duplicate_of_document_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetailRead(DocumentRead):
    """
    Respuesta detallada de un documento.

    Incluye campos extraidos, errores de validacion y eventos recientes.
    """

    extracted_fields: list[ExtractedFieldRead]
    validation_errors: list[DocumentValidationErrorRead]
    events: list[EventLogRead]


class DocumentListResponse(BaseModel):
    """
    Respuesta paginada para listar documentos.
    """

    items: list[DocumentRead]
    total: int
    limit: int
    offset: int