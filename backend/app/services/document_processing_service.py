import logging
import re
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.adapters.storage.local_storage import LocalStorageAdapter

from app.models import Document
from app.models.enums import ActorType, DocumentStatus, DocumentType

from app.repositories.document_repository import DocumentRepository
from app.repositories.event_log_repository import EventLogRepository
from app.repositories.extracted_field_repository import ExtractedFieldRepository
from app.repositories.validation_error_repository import ValidationErrorRepository
from app.repositories.validation_rule_repository import ValidationRuleRepository

from app.services.batch_status_service import BatchStatusService

logger = logging.getLogger("app.services.document_processing")


class DocumentProcessingService:
    """
    Servicio de procesamiento simulado de documentos.

    Este servicio representa el pipeline asincrono:
    - extraer texto
    - clasificar documento
    - extraer campos
    - calcular confianza
    - validar campos requeridos
    - dejar el documento en needs_review
    """

    DEFAULT_REQUIRED_FIELDS: dict[DocumentType, list[str]] = {
        DocumentType.INVOICE: ["vendor", "total", "currency", "document_date"],
        DocumentType.CONTRACT: ["contract_number", "person_name", "document_date"],
        DocumentType.ID_DOCUMENT: ["person_name", "document_date"],
        DocumentType.BANK_STATEMENT: ["person_name", "total", "currency", "document_date"],
        DocumentType.OTHER: [],
    }

    def __init__(self, db: Session):
        self.db = db
        self.storage_adapter = LocalStorageAdapter()
        self.document_repository = DocumentRepository(db)
        self.event_log_repository = EventLogRepository(db)
        self.extracted_field_repository = ExtractedFieldRepository(db)
        self.validation_error_repository = ValidationErrorRepository(db)
        self.validation_rule_repository = ValidationRuleRepository(db)
        self.batch_status_service = BatchStatusService(db)

    def process_document(
        self,
        *,
        document_id: uuid.UUID,
    ) -> None:
        """
        Procesa un documento previamente encolado.

        Si algo falla tecnicamente, marca el documento como failed y registra
        el error en auditoria.
        """
        document = self.db.get(Document, document_id)

        if document is None:
            logger.warning(
                "document_not_found",
                extra={"document_id": str(document_id)},
            )
            return

        if document.status != DocumentStatus.QUEUED:
            logger.info(
                "document_skipped_unexpected_status",
                extra={
                    "document_id": str(document_id),
                    "status": document.status,
                },
            )
            return

        try:
            self._mark_extraction_started(document)

            raw_text = self._extract_text(document)

            self.event_log_repository.create(
                organization_id=document.organization_id,
                entity_type="document",
                entity_id=document.id,
                event_type="extraction_finished",
                actor_type=ActorType.WORKER,
                payload={
                    "text_preview": raw_text[:120],
                },
            )

            document_type = self._classify_document(raw_text, document)
            extracted_fields = self._extract_fields(raw_text, document_type)
            confidence_score = self._calculate_confidence(
                document=document,
                extracted_fields=extracted_fields,
            )

            self.document_repository.update_processing_result(
                document=document,
                status=DocumentStatus.CLASSIFIED,
                document_type=document_type,
                confidence_score=confidence_score,
            )

            self.event_log_repository.create(
                organization_id=document.organization_id,
                entity_type="document",
                entity_id=document.id,
                event_type="classification_finished",
                actor_type=ActorType.WORKER,
                payload={
                    "document_type": document_type.value,
                    "confidence_score": confidence_score,
                },
            )

            self.extracted_field_repository.delete_for_document(
                document_id=document.id,
            )

            self.extracted_field_repository.create_many(
                document_id=document.id,
                fields=extracted_fields,
                confidence_score=confidence_score,
            )

            missing_fields = self._validate_required_fields(
                document=document,
                document_type=document_type,
                extracted_fields=extracted_fields,
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
                    organization_id=document.organization_id,
                    entity_type="document",
                    entity_id=document.id,
                    event_type="validation_failed",
                    actor_type=ActorType.WORKER,
                    payload={
                        "missing_fields": missing_fields,
                    },
                )
            else:
                self.event_log_repository.create(
                    organization_id=document.organization_id,
                    entity_type="document",
                    entity_id=document.id,
                    event_type="validation_passed",
                    actor_type=ActorType.WORKER,
                    payload={},
                )

            final_status = self._decide_final_status(
                confidence_score=confidence_score,
                missing_fields=missing_fields,
            )

            self.document_repository.update_status(
                document=document,
                status=final_status,
            )

            if final_status == DocumentStatus.APPROVED:
                self.event_log_repository.create(
                    organization_id=document.organization_id,
                    entity_type="document",
                    entity_id=document.id,
                    event_type="approved",
                    actor_type=ActorType.WORKER,
                    payload={
                        "reason": "auto_approved",
                        "confidence_score": confidence_score,
                    },
                )
            else:
                self.event_log_repository.create(
                    organization_id=document.organization_id,
                    entity_type="document",
                    entity_id=document.id,
                    event_type="needs_review",
                    actor_type=ActorType.WORKER,
                    payload={
                        "confidence_score": confidence_score,
                        "missing_fields": missing_fields,
                    },
                )
            
            self.batch_status_service.recalculate_for_batch(
                batch_id=document.batch_id,
                organization_id=document.organization_id,
            )

            self.db.commit()

        except Exception as exc:
            self.db.rollback()

            document = self.db.get(Document, document_id)

            if document is not None:
                document.status = DocumentStatus.FAILED

                self.event_log_repository.create(
                    organization_id=document.organization_id,
                    entity_type="document",
                    entity_id=document.id,
                    event_type="processing_failed",
                    actor_type=ActorType.WORKER,
                    payload={
                        "error": str(exc),
                    },
                )

                self.batch_status_service.recalculate_for_batch(
                    batch_id=document.batch_id,
                    organization_id=document.organization_id,
                )

                self.db.commit()

            logger.exception(
                "document_processing_failed",
                extra={"document_id": str(document_id)},
            )

            raise

    def _mark_extraction_started(
        self,
        document: Document,
    ) -> None:
        """
        Cambia el documento a extracting y registra el evento.
        """
        self.document_repository.update_status(
            document=document,
            status=DocumentStatus.EXTRACTING,
        )

        self.event_log_repository.create(
            organization_id=document.organization_id,
            entity_type="document",
            entity_id=document.id,
            event_type="extraction_started",
            actor_type=ActorType.WORKER,
            payload={},
        )

        self.db.flush()

    def _extract_text(
        self,
        document: Document,
    ) -> str:
        """
        Extrae texto de forma simulada.

        Para TXT lee contenido real. Para PDF/imagenes devuelve texto
        simulado porque el challenge no exige OCR real.
        """
        content = self.storage_adapter.read(storage_key=document.storage_key)

        if document.mime_type == "text/plain":
            return content.decode("utf-8", errors="ignore")

        if document.mime_type == "application/pdf":
            return "Simulated PDF invoice total 1500 MXN vendor Demo Vendor"

        if document.mime_type in {"image/png", "image/jpeg"}:
            return "Simulated image id document person name Demo User"

        return ""

    def _classify_document(
        self,
        text: str,
        document: Document,
    ) -> DocumentType:
        """
        Clasifica el documento usando reglas simples por palabras clave.
        """
        normalized_text = text.lower()
        normalized_filename = document.filename.lower()

        if "factura" in normalized_text or "invoice" in normalized_text:
            return DocumentType.INVOICE

        if "contrato" in normalized_text or "contract" in normalized_text:
            return DocumentType.CONTRACT

        if "bank" in normalized_text or "statement" in normalized_text:
            return DocumentType.BANK_STATEMENT

        if "id document" in normalized_text or "identificacion" in normalized_text:
            return DocumentType.ID_DOCUMENT

        if "invoice" in normalized_filename or "factura" in normalized_filename:
            return DocumentType.INVOICE

        return DocumentType.OTHER

    def _extract_fields(
        self,
        text: str,
        document_type: DocumentType,
    ) -> dict[str, str]:
        """
        Extrae campos simulados segun el tipo documental.
        """
        total = self._find_total(text)
        currency = self._find_currency(text)

        if document_type == DocumentType.INVOICE:
            return {
                "vendor": "Demo Vendor",
                "total": total or "0",
                "currency": currency or "MXN",
                "document_date": date.today().isoformat(),
            }

        if document_type == DocumentType.CONTRACT:
            return {
                "contract_number": "CONTRACT-001",
                "person_name": "Demo User",
                "document_date": date.today().isoformat(),
            }

        if document_type == DocumentType.ID_DOCUMENT:
            return {
                "person_name": "Demo User",
                "document_date": date.today().isoformat(),
            }

        if document_type == DocumentType.BANK_STATEMENT:
            return {
                "person_name": "Demo User",
                "total": total or "0",
                "currency": currency or "MXN",
                "document_date": date.today().isoformat(),
            }

        return {}

    def _calculate_confidence(
        self,
        *,
        document: Document,
        extracted_fields: dict[str, str],
    ) -> float:
        """
        Calcula una confianza simulada entre 0 y 1.
        """
        confidence_score = 0.92

        if document.mime_type != "text/plain":
            confidence_score -= 0.10

        if not extracted_fields:
            confidence_score -= 0.25

        return max(0.0, min(1.0, round(confidence_score, 2)))

    def _validate_required_fields(
        self,
        *,
        document: Document,
        document_type: DocumentType,
        extracted_fields: dict[str, str],
    ) -> list[str]:
        """
        Valida campos requeridos.

        Si la organizacion no tiene reglas configuradas, usa reglas default.
        """
        rule = self.validation_rule_repository.get_for_organization_and_type(
            organization_id=document.organization_id,
            document_type=document_type,
        )

        required_fields = (
            rule.required_fields
            if rule is not None
            else self.DEFAULT_REQUIRED_FIELDS[document_type]
        )

        return [
            field
            for field in required_fields
            if not extracted_fields.get(field)
        ]

    def _find_total(
        self,
        text: str,
    ) -> str | None:
        """
        Busca una cantidad despues de la palabra total.
        """
        match = re.search(r"total\s+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)

        if match is None:
            return None

        return match.group(1)

    def _find_currency(
        self,
        text: str,
    ) -> str | None:
        """
        Busca una moneda simple dentro del texto.
        """
        normalized_text = text.upper()

        if "MXN" in normalized_text:
            return "MXN"

        if "USD" in normalized_text:
            return "USD"

        return None
    
    def _decide_final_status(
        self,
        *,
        confidence_score: float,
        missing_fields: list[str],
    ) -> DocumentStatus:
        """
        Decide el estado final del pipeline automatico.

        Regla del challenge:
        - needs_review si confidence_score < 0.85
        - needs_review si faltan campos requeridos
        - approved si confidence_score >= 0.85 y no faltan campos
        """
        if confidence_score < 0.85:
            return DocumentStatus.NEEDS_REVIEW

        if missing_fields:
            return DocumentStatus.NEEDS_REVIEW

        return DocumentStatus.APPROVED