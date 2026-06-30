import uuid

from sqlalchemy.orm import Session

from app.models import Organization
from app.models.enums import DocumentStatus, DocumentType
from app.repositories.document_repository import DocumentRepository
from app.repositories.event_log_repository import EventLogRepository
from app.repositories.extracted_field_repository import ExtractedFieldRepository
from app.repositories.validation_error_repository import ValidationErrorRepository
from app.schemas.document import DocumentDetailRead, DocumentListResponse


class DocumentNotFoundError(Exception):
    """
    Se lanza cuando el documento no existe dentro de la organizacion actual.
    """


class DocumentQueryService:
    """
    Servicio de consulta de documentos.

    Mantiene el aislamiento multi-tenant y arma respuestas detalladas para la API.
    """

    def __init__(self, db: Session):
        self.db = db
        self.document_repository = DocumentRepository(db)
        self.extracted_field_repository = ExtractedFieldRepository(db)
        self.validation_error_repository = ValidationErrorRepository(db)
        self.event_log_repository = EventLogRepository(db)

    def list_documents(
        self,
        *,
        current_organization: Organization,
        status: DocumentStatus | None,
        document_type: DocumentType | None,
        limit: int,
        offset: int,
    ) -> DocumentListResponse:
        """
        Lista documentos de la organizacion autenticada.
        """
        items = self.document_repository.list_for_organization(
            organization_id=current_organization.id,
            status=status,
            document_type=document_type,
            limit=limit,
            offset=offset,
        )

        total = self.document_repository.count_for_organization(
            organization_id=current_organization.id,
            status=status,
            document_type=document_type,
        )

        return DocumentListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_document_detail(
        self,
        *,
        current_organization: Organization,
        document_id: uuid.UUID,
    ) -> DocumentDetailRead:
        """
        Devuelve detalle completo del documento.

        Incluye datos principales, campos extraidos, errores y eventos.
        """
        document = self.document_repository.get_by_id_for_organization(
            document_id=document_id,
            organization_id=current_organization.id,
        )

        if document is None:
            raise DocumentNotFoundError("Document not found")

        extracted_fields = self.extracted_field_repository.list_for_document(
            document_id=document.id,
        )

        validation_errors = self.validation_error_repository.list_for_document(
            document_id=document.id,
        )

        events = self.event_log_repository.list_for_entity(
            organization_id=current_organization.id,
            entity_type="document",
            entity_id=document.id,
        )

        return DocumentDetailRead(
            **document.__dict__,
            extracted_fields=extracted_fields,
            validation_errors=validation_errors,
            events=events,
        )

    def list_document_events(
        self,
        *,
        current_organization: Organization,
        document_id: uuid.UUID,
    ):
        """
        Lista solo eventos del documento.
        """
        document = self.document_repository.get_by_id_for_organization(
            document_id=document_id,
            organization_id=current_organization.id,
        )

        if document is None:
            raise DocumentNotFoundError("Document not found")

        return self.event_log_repository.list_for_entity(
            organization_id=current_organization.id,
            entity_type="document",
            entity_id=document.id,
        )