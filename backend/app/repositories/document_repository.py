import uuid

from sqlalchemy.orm import Session

from app.models import Document
from app.models.enums import DocumentStatus


class DocumentRepository:
    """
    Repositorio para la gestión de persistencia de entidades 'Document'.
    Encapsula las operaciones de base de datos relacionadas con los archivos subidos.
    """
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        batch_id: uuid.UUID,
        filename: str,
        mime_type: str,
        file_size: int,
        checksum_sha256: str,
        source_reference: str | None,
        storage_key: str,
    ) -> Document:
        """
        Registra un nuevo documento asociado a un lote (batch).
        
        Inicializa el documento con el estado 'UPLOADED'. Se utiliza 'flush' y 
        'refresh' para asegurar la integridad de la transacción y la recuperación 
        de los valores generados por la base de datos (como el ID del documento).
        """
        document = Document(
            organization_id=organization_id,
            batch_id=batch_id,
            filename=filename,
            mime_type=mime_type,
            file_size=file_size,
            checksum_sha256=checksum_sha256,
            source_reference=source_reference,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED,
        )

        self.db.add(document)
        self.db.flush()
        self.db.refresh(document)

        return document