import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BatchStatus


class BatchCreate(BaseModel):
    """
    Esquema para la validación de entrada de datos durante la creación de un nuevo Batch. 
    Define las restricciones de integridad para los campos requeridos por el cliente. 
    """
    # Se utiliza default_factory=dict para asegurar una nueva instancia de diccionario
    # por cada objeto, evitando errores de referncia mutable en memoria. 
    name: str = Field(min_length=2, max_length=255)
    source: str = Field(min_length=2, max_length=120)
    # En la API se manda como "metadata"
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchRead(BaseModel):
    """
    Esquema de salida para la serialización de objetos Batch desde la base de datos
    """
    # Configuración de Pydantic v2: from_atributes=True permite que el modelo 
    # pueda leer datos directamente desde objetos de SQLAlchemy. 
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    source: str
    status: BatchStatus

    # En el modelo SQLAlchemy se llama metadata_,
    # pero en la respuesta JSON queremos mostrar "metadata"
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_",
    )
    created_at: datetime
    updated_at: datetime