import uuid

from sqlalchemy.orm import Session

from app.models import Organization
from app.models.enums import ActorType, DocumentType
from app.repositories.document_repository import DocumentRepository
from app.repositories.event_log_repository import EventLogRepository
from app.repositories.extracted_field_repository import ExtractedFieldRepository
from app.repositories.validation_error_repository import ValidationErrorRepository
from app.repositories.validation_rule_repository import ValidationRuleRepository
from app.schemas.document import DocumentFieldsUpdate


class DocumentNotFoundForReviewError(Exception):
    """
    Se lanza cuando el documento no existe dentro de la organizacion actual.
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