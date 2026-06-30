import hashlib
import uuid
from pathlib import PurePath

from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.storage.local_storage import LocalStorageAdapter
from app.core.config import get_settings
from app.models import Organization
from app.repositories.batch_repository import BatchRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.idempotency_repository import IdempotencyRepository
from app.schemas.document import DocumentRead

from app.adapters.queue.document_queue import DocumentQueue
from app.models.enums import DocumentStatus

from app.services.batch_status_service import BatchStatusService


class BatchNotFoundForUploadError(Exception):
    """Se lanza cuando el batch no existe o no pertenece a la organización."""


class InvalidFileTypeError(Exception):
    """Se lanza cuando el MIME type del archivo no está permitido."""


class FileTooLargeError(Exception):
    """Se lanza cuando el archivo excede el tamaño máximo configurado."""


class DuplicateDocumentError(Exception):
    """Se lanza cuando la base de datos bloquea un duplicado no esperado."""


class IdempotencyConflictError(Exception):
    """
    Se lanza cuando una misma Idempotency-Key se reutiliza con otra petición.

    Una key debe representar una sola intención. Si cambia el archivo o los
    metadatos relevantes, no podemos devolver la respuesta anterior.
    """


class DocumentService:
    """
    Contiene la lógica de negocio del upload de documentos.

    Responsabilidades principales:
    - Validar tenant usando el batch.
    - Validar tipo y tamaño del archivo.
    - Calcular checksum SHA-256.
    - Resolver idempotencia.
    - Detectar duplicados por organización.
    - Guardar archivo en storage local.
    - Crear el registro Document.
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.batch_repository = BatchRepository(db)
        self.document_repository = DocumentRepository(db)
        self.idempotency_repository = IdempotencyRepository(db)
        self.storage_adapter = LocalStorageAdapter()
        self.document_queue = DocumentQueue()
        self.batch_status_service = BatchStatusService(db)

    async def upload_document(
        self,
        *,
        current_organization: Organization,
        batch_id: uuid.UUID,
        file: UploadFile,
        source_reference: str | None,
        idempotency_key: str | None,
    ):
        """
        Sube un documento a un batch.

        Si llega una Idempotency-Key repetida con la misma petición,
        regresa la misma respuesta guardada sin crear otro documento.
        """
        batch = self.batch_repository.get_by_id_for_organization(
            batch_id=batch_id,
            organization_id=current_organization.id,
        )

        if batch is None:
            raise BatchNotFoundForUploadError("Batch not found")

        mime_type = file.content_type or "application/octet-stream"

        allowed_mime_types = {
            value.strip()
            for value in self.settings.ALLOWED_UPLOAD_MIME_TYPES.split(",")
        }

        if mime_type not in allowed_mime_types:
            raise InvalidFileTypeError(
                f"File type '{mime_type}' is not allowed"
            )

        file_content = await file.read()
        file_size = len(file_content)

        if file_size > self.settings.MAX_UPLOAD_SIZE_BYTES:
            raise FileTooLargeError("File exceeds maximum allowed size")

        checksum_sha256 = hashlib.sha256(file_content).hexdigest()
        filename = PurePath(file.filename or "uploaded_file").name

        request_hash = self._build_upload_request_hash(
            batch_id=batch.id,
            filename=filename,
            mime_type=mime_type,
            file_size=file_size,
            checksum_sha256=checksum_sha256,
            source_reference=source_reference,
        )

        if idempotency_key is not None:
            existing_record = self.idempotency_repository.get_by_key(
                organization_id=current_organization.id,
                idempotency_key=idempotency_key,
            )

            if existing_record is not None:
                if existing_record.request_hash != request_hash:
                    raise IdempotencyConflictError(
                        "Idempotency-Key was already used for a different request"
                    )

                return existing_record.response_snapshot

        existing_document = (
            self.document_repository.get_canonical_by_checksum_for_organization(
                organization_id=current_organization.id,
                checksum_sha256=checksum_sha256,
            )
        )

        is_duplicate_candidate = existing_document is not None
        duplicate_of_document_id = (
            existing_document.id if existing_document is not None else None
        )

        storage_key = (
            f"{current_organization.id}/{batch.id}/"
            f"{checksum_sha256}-{filename}"
        )

        try:
            self.storage_adapter.save(
                storage_key=storage_key,
                content=file_content,
            )

            document = self.document_repository.create(
                organization_id=current_organization.id,
                batch_id=batch.id,
                filename=filename,
                mime_type=mime_type,
                file_size=file_size,
                checksum_sha256=checksum_sha256,
                source_reference=source_reference,
                storage_key=storage_key,
                is_duplicate_candidate=is_duplicate_candidate,
                duplicate_of_document_id=duplicate_of_document_id,
            )

            document = self.document_repository.update_status(
                document=document,
                status=DocumentStatus.QUEUED,
            )

            self.batch_status_service.recalculate_for_batch(
                batch_id=batch.id,
                organization_id=current_organization.id,
            )

            response_snapshot = jsonable_encoder(
                DocumentRead.model_validate(document)
            )

            if idempotency_key is not None:
                self.idempotency_repository.create(
                    organization_id=current_organization.id,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_snapshot=response_snapshot,
                )

            self.db.commit()

            self.document_queue.enqueue_document_processing(
                document_id=document.id,
            )

            return response_snapshot

        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateDocumentError(
                "Document with same checksum already exists"
            ) from exc

        except Exception:
            self.db.rollback()
            raise

    def _build_upload_request_hash(
        self,
        *,
        batch_id: uuid.UUID,
        filename: str,
        mime_type: str,
        file_size: int,
        checksum_sha256: str,
        source_reference: str | None,
    ) -> str:
        """
        Construye un hash estable de la intención del upload.

        No guardamos el archivo completo en idempotencia. Guardamos una huella
        de los datos importantes para saber si la petición repetida es igual.
        """
        raw_value = "|".join(
            [
                str(batch_id),
                filename,
                mime_type,
                str(file_size),
                checksum_sha256,
                source_reference or "",
            ]
        )

        return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()