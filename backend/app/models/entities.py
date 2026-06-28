from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    ActorType,
    BatchStatus,
    DocumentStatus,
    DocumentType,
    FieldSource,
    OrganizationStatus,
)


class TimestampMixin:
    """
    Mixin para proveer trazabilidad temporal estándar a las entidades de la base 
    de datos. 
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Organization(Base, TimestampMixin):
    """
    Representa la entidad multi-tenant raíz del sistema. 
    Define el alcance de los recursos y el estado operativo de cada cliente 
    """
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    #Identificador único legible 
    slug: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    # Estado de la organización para control de acceso 
    status: Mapped[OrganizationStatus] = mapped_column(
        SAEnum(
            OrganizationStatus,
            name="organization_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
    )

    # Relaciones de cascada para asegurar la integridad referncial al eliminar un tenant 
    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    batches: Mapped[list["Batch"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    validation_rules: Mapped[list["ValidationRule"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class ApiKey(Base):
    """
    Almacena hashes de llaves de API para autenticación segura entre servicios externos. 
    """
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Se almacena únicamente el hash por seguridad 
    key_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )

    # Prefijo para identificación rápida sin exponer el hash completo 
    prefix: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Timestamp opcional para revocación lógica sin eliminar el registro del sistema
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="api_keys",
    )


class Batch(Base, TimestampMixin):
    """
    Agrupación lógica de documentos para procesamiento masivo y trazabilidad 
    """
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Indica el origen de la ingesta
    source: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="api",
    )

    status: Mapped[BatchStatus] = mapped_column(
        SAEnum(
            BatchStatus,
            name="batch_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=BatchStatus.CREATED,
        index=True,
    )

    # Campo flexible para configuraciones específicas de procesamiento por batch 
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="batches",
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_batches_org_status", "organization_id", "status"),
    )


class Document(Base, TimestampMixin):
    """
    Entidad principal de ingesta. Representa un archivo individual y su ciclo de vida de procesamiento 
    """
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)

    file_size: Mapped[int] = mapped_column(nullable=False)

    # Checksum para detección de duplicados e integridad del archivo 
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            name="document_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        index=True,
    )

    document_type: Mapped[DocumentType | None] = mapped_column(
        SAEnum(
            DocumentType,
            name="document_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=True,
        index=True,
    )

    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Clave de almacenamiento en el StorageAdapter
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    source_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    #identificación de duplicados para optimización de almacenamiento 
    is_duplicate_candidate: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    duplicate_of_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="documents",
    )

    batch: Mapped["Batch"] = relationship(
        back_populates="documents",
    )

    # Relación autoreferencial para enlazar duplicados con el documento canónico 
    duplicate_of_document: Mapped["Document | None"] = relationship(
        "Document",
        remote_side=lambda: [Document.id],
        uselist=False,
    )

    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    validation_errors: Mapped[list["ValidationError"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_documents_org_status", "organization_id", "status"),
        Index("ix_documents_batch_status", "batch_id", "status"),
        Index("ix_documents_org_checksum", "organization_id", "checksum_sha256"),
        # Constraint de unicidad para evitar documentos duplicados por organización
        Index(
            "uq_documents_org_checksum_canonical",
            "organization_id",
            "checksum_sha256",
            unique=True,
            postgresql_where=text("is_duplicate_candidate = false"),
        ),
    )


class ExtractedField(Base, TimestampMixin):
    """
    Almacena los datos extraídos de un documento tras la fase de procesamiento 
    """
    __tablename__ = "extracted_fields"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    key_field: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Determina si el dato proviene de un proceso automático o de intervención humana 
    source: Mapped[FieldSource] = mapped_column(
        SAEnum(
            FieldSource,
            name="field_source",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=FieldSource.SYSTEM,
    )

    # Trazabilidad para correcciones manuales 
    corrected_by: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    corrected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    document: Mapped["Document"] = relationship(
        back_populates="extracted_fields",
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "key_field",
            name="uq_extracted_fields_document_key",
        ),
    )


class ValidationRule(Base, TimestampMixin):
    """
    Define las reglas de negocio de validación para tipos documentales por organización 
    """
    __tablename__ = "validation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(
            DocumentType,
            name="validation_rule_document_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    # Almacena una lista de campos obligatorios para el tipo documental
    required_fields: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="validation_rules",
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "document_type",
            name="uq_validation_rules_org_doc_type",
        ),
    )


class ValidationError(Base):
    """
    Registro de errores detectados durante la validación de un documento 
    """
    __tablename__ = "validation_errors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    key_field: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    #Código de error para categorización programática a fallos
    code: Mapped[str] = mapped_column(String(120), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    document: Mapped["Document"] = relationship(
        back_populates="validation_errors",
    )


class EventLog(Base):
    """
    Bitácora de eventos del sistema para fines de auditoría 
    """
    __tablename__ = "event_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identificación genérica del tipo de entidad sobre la cual ocurre el evento 
    entity_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    # Clasificación del actor
    actor_type: Mapped[ActorType] = mapped_column(
        SAEnum(
            ActorType,
            name="actor_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=ActorType.SYSTEM,
    )

    actor_id: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    # Payload flexible para capturar contexto detallado del evento 
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_event_logs_org_entity",
            "organization_id",
            "entity_type",
            "entity_id",
        ),
    )


class IdempotencyRecord(Base):
    """
    Almacena registros de idempotencia para asegurar que peticiones duplicadas
    no tengan efectos secundarios no deseados en el procesamiento 
    """
    __tablename__ = "idempotency_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Hash del cuerpo de la petición para validación de consistencia 
    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Snapshot de la respuesta original para devolverla si la petición se repite
    response_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_idempotency_org_key",
        ),
        Index(
            "ix_idempotency_org_request_hash",
            "organization_id",
            "request_hash",
        ),
    )