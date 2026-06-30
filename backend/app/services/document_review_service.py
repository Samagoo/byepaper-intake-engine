import uuid

from sqlalchemy.orm import Session

from app.models import Organization
from app.models.enums import ActorType, DocumentType, DocumentStatus

from app.repositories.document_repository import DocumentRepository
from app.repositories.event_log_repository import EventLogRepository
from app.repositories.extracted_field_repository import ExtractedFieldRepository
from app.repositories.validation_error_repository import ValidationErrorRepository
from app.repositories.validation_rule_repository import ValidationRuleRepository

from app.schemas.document import DocumentFieldsUpdate

from app.adapters.queue.document_queue import DocumentQueue


class DocumentNotFoundForReviewError(Exception):
    """
    Se lanza cuando el documento no existe dentro de la organizacion actual.
    """

class DocumentInvalidStateForReviewError(Exception):
    """
    Se lanza cuando el documento no esta en needs_review.
    """


class DocumentApprovalBlockedError(Exception):
    """
    Se lanza cuando faltan campos requeridos y no se puede aprobar.
    """

class DocumentRetryInvalidStateError(Exception):
    """
    Se lanza cuando se intenta reintentar un documento que no esta failed.
    """

class DocumentReviewService:
    """
    Servicio para revision humana de documentos.

    Permite corregir campos extraidos y volver a validar reglas de negocio.
    """

    DEFAULT_REQUIRED_FIELDS: dict[DocumentType, list[str]] = {
        DocumentType.INVOICE: ["vendor", "total", "currency", "document_date"],
        DocumentType.CONTRACT: ["contract_number", "person_name", "document_date"],
        DocumentType.ID_DOCUMENT: ["person_name", "document_date"],
        DocumentType.BANK_STATEMENT: [
            "person_name",
            "total",
            "currency",
            "document_date",
        ],
        DocumentType.OTHER: [],
    }

    def __init__(self, db: Session):
        self.db = db
        self.document_repository = DocumentRepository(db)
        self.extracted_field_repository = ExtractedFieldRepository(db)
        self.validation_error_repository = ValidationErrorRepository(db)
        self.validation_rule_repository = ValidationRuleRepository(db)
        self.event_log_repository = EventLogRepository(db)
        self.document_queue = DocumentQueue()

    def update_fields(
        self,
        *,
        current_organization: Organization,
        document_id: uuid.UUID,
        data: DocumentFieldsUpdate,
    ):
        """
        Actualiza campos del documento y vuelve a validar.

        El documento siempre se busca por document_id + organization_id para
        mantener aislamiento multi-tenant.
        """
        document = self.document_repository.get_by_id_for_organization(
            document_id=document_id,
            organization_id=current_organization.id,
        )

        if document is None:
            raise DocumentNotFoundForReviewError("Document not found")

        try:
            self.extracted_field_repository.upsert_human_fields(
                document_id=document.id,
                fields=data.fields,
                reviewer_id=data.reviewer_id,
            )

            current_fields = self.extracted_field_repository.list_for_document(
                document_id=document.id,
            )

            fields_by_key = {
                field.key_field: field.value
                for field in current_fields
            }

            missing_fields = self._get_missing_fields(
                organization_id=current_organization.id,
                document_type=document.document_type or DocumentType.OTHER,
                fields_by_key=fields_by_key,
            )

            self.validation_error_repository.delete_for_document(
                document_id=document.id,
            )

            if missing_fields:
                self.validation_error_repository.create_many(
                    document_id=document.id,
                    missing_fields=missing_fields,
                )

            self.event_log_repository.create(
                organization_id=current_organization.id,
                entity_type="document",
                entity_id=document.id,
                event_type="review_updated",
                actor_type=ActorType.REVIEWER,
                actor_id=data.reviewer_id,
                payload={
                    "updated_fields": list(data.fields.keys()),
                    "missing_fields": missing_fields,
                },
            )

            self.db.commit()

            return {
                "document_id": str(document.id),
                "status": document.status.value,
                "updated_fields": list(data.fields.keys()),
                "missing_fields": missing_fields,
            }

        except Exception:
            self.db.rollback()
            raise

    def _get_missing_fields(
        self,
        *,
        organization_id: uuid.UUID,
        document_type: DocumentType,
        fields_by_key: dict[str, str | None],
    ) -> list[str]:
        """
        Calcula campos faltantes usando regla de DB o defaults.
        """
        rule = self.validation_rule_repository.get_for_organization_and_type(
            organization_id=organization_id,
            document_type=document_type,
        )

        required_fields = (
            rule.required_fields
            if rule is not None
            else self.DEFAULT_REQUIRED_FIELDS[document_type]
        )

        return [
            key_field
            for key_field in required_fields
            if not fields_by_key.get(key_field)
        ]
    
    def approve_document(
        self,
        *,
        current_organization: Organization,
        document_id: uuid.UUID,
        reviewer_id: str | None,
    ):
        """
        Aprueba manualmente un documento en needs_review.

        Antes de aprobar, valida que no falten campos requeridos.
        """
        document = self.document_repository.get_by_id_for_organization(
            document_id=document_id,
            organization_id=current_organization.id,
        )

        if document is None:
            raise DocumentNotFoundForReviewError("Document not found")

        if document.status != DocumentStatus.NEEDS_REVIEW:
            raise DocumentInvalidStateForReviewError(
                "Document must be in needs_review before approval"
            )

        current_fields = self.extracted_field_repository.list_for_document(
            document_id=document.id,
        )

        fields_by_key = {
            field.key_field: field.value
            for field in current_fields
        }

        missing_fields = self._get_missing_fields(
            organization_id=current_organization.id,
            document_type=document.document_type or DocumentType.OTHER,
            fields_by_key=fields_by_key,
        )

        self.validation_error_repository.delete_for_document(
            document_id=document.id,
        )

        if missing_fields:
            self.validation_error_repository.create_many(
                document_id=document.id,
                missing_fields=missing_fields,
            )
            self.db.commit()

            raise DocumentApprovalBlockedError(
                "Document has missing required fields"
            )

        try:
            self.document_repository.update_status(
                document=document,
                status=DocumentStatus.APPROVED,
            )

            self.event_log_repository.create(
                organization_id=current_organization.id,
                entity_type="document",
                entity_id=document.id,
                event_type="approved",
                actor_type=ActorType.REVIEWER,
                actor_id=reviewer_id,
                payload={},
            )

            self.db.commit()

            return {
                "document_id": str(document.id),
                "status": document.status.value,
            }

        except Exception:
            self.db.rollback()
            raise

    def reject_document(
        self,
        *,
        current_organization: Organization,
        document_id: uuid.UUID,
        reviewer_id: str | None,
        reason: str | None,
    ):
        """
        Rechaza manualmente un documento en needs_review.

        Rejected es decision humana. Failed es error tecnico.
        """
        document = self.document_repository.get_by_id_for_organization(
            document_id=document_id,
            organization_id=current_organization.id,
        )

        if document is None:
            raise DocumentNotFoundForReviewError("Document not found")

        if document.status != DocumentStatus.NEEDS_REVIEW:
            raise DocumentInvalidStateForReviewError(
                "Document must be in needs_review before rejection"
            )

        try:
            self.document_repository.update_status(
                document=document,
                status=DocumentStatus.REJECTED,
            )

            self.event_log_repository.create(
                organization_id=current_organization.id,
                entity_type="document",
                entity_id=document.id,
                event_type="rejected",
                actor_type=ActorType.REVIEWER,
                actor_id=reviewer_id,
                payload={
                    "reason": reason,
                },
            )

            self.db.commit()

            return {
                "document_id": str(document.id),
                "status": document.status.value,
                "reason": reason,
            }

        except Exception:
            self.db.rollback()
            raise

    def retry_document(
        self,
        *,
        current_organization: Organization,
        document_id: uuid.UUID,
        reviewer_id: str | None,
    ):
        """
        Reintenta el procesamiento de un documento fallido.

        Solo documentos en failed pueden regresar a queued.
        """
        document = self.document_repository.get_by_id_for_organization(
            document_id=document_id,
            organization_id=current_organization.id,
        )

        if document is None:
            raise DocumentNotFoundForReviewError("Document not found")

        if document.status != DocumentStatus.FAILED:
            raise DocumentRetryInvalidStateError(
                "Only failed documents can be retried"
            )

        try:
            self.document_repository.update_status(
                document=document,
                status=DocumentStatus.QUEUED,
            )

            self.event_log_repository.create(
                organization_id=current_organization.id,
                entity_type="document",
                entity_id=document.id,
                event_type="retry_requested",
                actor_type=ActorType.REVIEWER,
                actor_id=reviewer_id,
                payload={},
            )

            self.db.commit()

            self.document_queue.enqueue_document_processing(
                document_id=document.id,
            )

            return {
                "document_id": str(document.id),
                "status": document.status.value,
            }

        except Exception:
            self.db.rollback()
            raise