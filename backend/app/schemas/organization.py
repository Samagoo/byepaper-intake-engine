import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import OrganizationStatus


class OrganizationCreate(BaseModel):
    """
    Schema para la creación de una nueva organización.
    Valida los datos de entrada antes de ser persistidos en la base de datos.
    """
    # Nombre visible de la organización.
    name: str = Field(min_length=2, max_length=255)

    # Slug legible y único.
    slug: str = Field(min_length=2, max_length=120)

    # Estado inicial de la organización.
    # Por defecto será active.
    status: OrganizationStatus = OrganizationStatus.ACTIVE

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        """
        Normaliza y valida el slug.

        Permitimos letras minúsculas, números, guiones medios
        """
        normalized = value.strip().lower()

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalized):
            raise ValueError(
                "Slug must contain lowercase letters, numbers and single hyphens only"
            )

        return normalized


class OrganizationRead(BaseModel):
    """
    Schema para la serialización de organizaciones en respuestas de la API.
    Utiliza el modo 'from_attributes' para mapear directamente desde modelos SQLAlchemy.
    """
    # Permite convertir modelos ORM de SQLAlchemy a respuestas Pydantic.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime