import hashlib
import uuid
from pathlib import PurePath

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models import Organization
from app.repositories.batch_repository import BatchRepository
from app.repositories.document_repository import DocumentRepository


class BatchNotFoundForUploadError(Exception):
    """
    Excepción lanzada cuando el Batch destino no existe o no pertenece a la organización.
    """
    pass


class DocumentService:
    """
    Capa de servicio para la gestión del ciclo de vida de los documentos.
    Coordina la validación del lote destino y la persistencia de los metadatos del archivo.
    """
    def __init__(self, db: Session):
        self.db = db
        self.batch_repository = BatchRepository(db)
        self.document_repository = DocumentRepository(db)

    async def upload_document(
        self,
        *,
        current_organization: Organization,
        batch_id: uuid.UUID,
        file: UploadFile,
        source_reference: str | None,
    ):
        """
        Gestiona el registro de un documento subido dentro de una transacción atómica.
        
        Verifica la pertenencia del lote a la organización antes de procesar el archivo.
        Implementa una lectura asíncrona del buffer del archivo para determinar metadatos 
        previo a la persistencia.
        """
        # Verificación de seguridad multi-tenancy: el Batch debe existir y pertenecer al usuario
        batch = self.batch_repository.get_by_id_for_organization(
            batch_id=batch_id,
            organization_id=current_organization.id,
        )

        if batch is None:
            raise BatchNotFoundForUploadError("Batch not found")

        file_content = await file.read()
        file_size = len(file_content)
        checksum_sha256 = hashlib.sha256(file_content).hexdigest()

        filename = PurePath(file.filename or "uploaded_file").name
        mime_type = file.content_type or "application/octet-stream"

        storage_key = (
            f"local/{current_organization.id}/{batch.id}/"
            f"{checksum_sha256}-{filename}"
        )

        try:
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

        except Exception:
            self.db.rollback()
            raise