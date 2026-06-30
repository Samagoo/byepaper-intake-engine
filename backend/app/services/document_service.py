import hashlib
import uuid
from pathlib import PurePath

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.storage.local_storage import LocalStorageAdapter
from app.core.config import get_settings
from app.models import Organization
from app.repositories.batch_repository import BatchRepository
from app.repositories.document_repository import DocumentRepository

class BatchNotFoundForUploadError(Exception): pass
class InvalidFileTypeError(Exception): pass
class FileTooLargeError(Exception): pass
class DuplicateDocumentError(Exception): pass

class DocumentService:
    """
    Servicio de orquestación para la ingesta y persistencia documental.
    
    Este servicio actúa como un 'facade' que valida reglas de negocio, 
    calcula la integridad de archivos, gestiona el almacenamiento físico 
    y asegura la consistencia en la base de datos relacional.
    """
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.batch_repository = BatchRepository(db)
        self.document_repository = DocumentRepository(db)
        self.storage_adapter = LocalStorageAdapter()

    async def upload_document(
        self,
        *,
        current_organization: Organization,
        batch_id: uuid.UUID,
        file: UploadFile,
        source_reference: str | None,
    ):
        """
        Procesa la subida de un documento con validaciones de seguridad y negocio.
        
        Flujo de ejecución:
        1. Validación de existencia del lote (Multi-tenant).
        2. Validación de tipo MIME y tamaño máximo.
        3. Cálculo de checksum (SHA-256) para idempotencia.
        4. Persistencia física en storage.
        5. Registro de metadatos en base de datos.
        """
        batch = self.batch_repository.get_by_id_for_organization(
            batch_id=batch_id,
            organization_id=current_organization.id,
        )
        if batch is None:
            raise BatchNotFoundForUploadError("Batch not found")

        # Validación estricta de tipo MIME
        mime_type = file.content_type or "application/octet-stream"
        allowed_mime_types = {
            value.strip() for value in self.settings.ALLOWED_UPLOAD_MIME_TYPES.split(",")
        }
        if mime_type not in allowed_mime_types:
            raise InvalidFileTypeError(f"File type '{mime_type}' is not allowed")

        # Lectura de bytes para validación y persistencia
        file_content = await file.read()
        file_size = len(file_content)
        if file_size > self.settings.MAX_UPLOAD_SIZE_BYTES:
            raise FileTooLargeError("File exceeds maximum allowed size")

        # Cálculo de integridad y generación de ruta de almacenamiento
        checksum_sha256 = hashlib.sha256(file_content).hexdigest()
        filename = PurePath(file.filename or "uploaded_file").name
        storage_key = (
            f"{current_organization.id}/{batch.id}/"
            f"{checksum_sha256}-{filename}"
        )

        try:
            # Persistencia física previo al registro en BD
            self.storage_adapter.save(storage_key=storage_key, content=file_content)

            document = self.document_repository.create(
                organization_id=current_organization.id,
                batch_id=batch.id,
                filename=filename,
                mime_type=mime_type,
                file_size=file_size,
                checksum_sha256=checksum_sha256,
                source_reference=source_reference,
                storage_key=storage_key,
            )

            self.db.commit()
            return document

        except IntegrityError as exc:
            # Captura de colisiones (ej: checksum duplicado en la misma tabla)
            self.db.rollback()
            raise DuplicateDocumentError("Document with same checksum already exists") from exc

        except Exception:
            self.db.rollback()
            raise