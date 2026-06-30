import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentType


class ValidationRuleUpsert(BaseModel):
    """
    Payload para crear o actualizar una regla de validacion.

    required_fields define que campos son obligatorios para un tipo documental.
    """

    document_type: DocumentType
    required_fields: list[str] = Field(default_factory=list)


class ValidationRuleRead(BaseModel):
    """
    Respuesta de una regla de validacion guardada.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    document_type: DocumentType
    required_fields: list[str]
    created_at: datetime
    updated_at: datetime