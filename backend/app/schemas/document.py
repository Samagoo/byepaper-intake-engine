import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus, DocumentType


class DocumentRead(BaseModel):
    """
    Esquema de serialización para la lectura de entidades 'Document'.
    
    Proporciona una vista pública de los metadatos del archivo, incluyendo su estado 
    en el pipeline de procesamiento y referencias de almacenamiento.
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