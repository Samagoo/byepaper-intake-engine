import uuid

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Document
from app.models.enums import DocumentStatus


class DocumentRepository:
    """
    Encapsula operaciones de base de datos relacionadas con documentos.

    Esta capa no decide reglas de negocio. Solo sabe crear y consultar
    documentos usando SQLAlchemy.
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
        is_duplicate_candidate: bool = False,
        duplicate_of_document_id: uuid.UUID | None = None,
    ) -> Document:
        """
        Crea un documento.

        Si is_duplicate_candidate es True, el documento representa una subida
        repetida detectada por checksum dentro de la misma organización.
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
            is_duplicate_candidate=is_duplicate_candidate,
            duplicate_of_document_id=duplicate_of_document_id,
        )

        self.db.add(document)
        self.db.flush()
        self.db.refresh(document)

        return document

    def get_canonical_by_checksum_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        checksum_sha256: str,
    ) -> Document | None:
        """
        Busca el documento original con el mismo checksum.

        Solo buscamos dentro de la misma organización. Dos organizaciones
        distintas pueden subir el mismo archivo sin bloquearse entre ellas.
        """
        statement = select(Document).where(
            Document.organization_id == organization_id,
            Document.checksum_sha256 == checksum_sha256,
            Document.is_duplicate_candidate.is_(False),
        )

        return self.db.execute(statement).scalar_one_or_none()
    
    def update_status(
        self,
        *,
        document: Document,
        status: DocumentStatus,
    ) -> Document:
        """
        Actualiza el estado actual del documento.

        El repository solo modifica el dato. La decisión de cuándo cambiar
        de estado pertenece al service o al worker.
        """
        document.status = status

        self.db.flush()
        self.db.refresh(document)

        return document
    
    def update_processing_result(
        self,
        *,
        document: Document,
        status: DocumentStatus,
        document_type,
        confidence_score: float,
    ) -> Document:
        """
        Guarda el resultado principal del procesamiento.

        Aqui se actualiza el tipo documental, el confidence_score y el estado
        final del pipeline automatico.
        """
        document.status = status
        document.document_type = document_type
        document.confidence_score = confidence_score

        self.db.flush()
        self.db.refresh(document)

        return document
    
    def get_by_id_for_organization(
        self,
        *,
        document_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Document | None:
        """
        Busca un documento filtrando por organizacion.

        Esta es la regla multi-tenant importante:
        nunca consultar un documento solo por id.
        """
        statement = select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )

        return self.db.execute(statement).scalar_one_or_none()

    def list_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        status: DocumentStatus | None,
        document_type,
        limit: int,
        offset: int,
    ) -> list[Document]:
        """
        Lista documentos de una organizacion con filtros opcionales.
        """
        statement = select(Document).where(
            Document.organization_id == organization_id,
        )

        if status is not None:
            statement = statement.where(Document.status == status)

        if document_type is not None:
            statement = statement.where(Document.document_type == document_type)

        statement = (
            statement.order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.execute(statement).scalars().all())

    def count_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        status: DocumentStatus | None,
        document_type,
    ) -> int:
        """
        Cuenta documentos de una organizacion aplicando los mismos filtros.
        """
        from sqlalchemy import func

        statement = select(func.count()).select_from(Document).where(
            Document.organization_id == organization_id,
        )

        if status is not None:
            statement = statement.where(Document.status == status)

        if document_type is not None:
            statement = statement.where(Document.document_type == document_type)

        return self.db.execute(statement).scalar_one()
    
    def list_statuses_for_batch(
        self,
        *,
        batch_id: uuid.UUID,
    ) -> list[DocumentStatus]:
        """
        Devuelve los estados actuales de todos los documentos de un batch.

        Esta informacion se usa para derivar el estado del batch.
        """
        statement = select(Document.status).where(
            Document.batch_id == batch_id,
        )

        return list(self.db.execute(statement).scalars().all())
    
    def count_by_status_for_batch(
        self,
        *,
        batch_id: uuid.UUID,
    ) -> dict[str, int]:
        """
        Cuenta documentos agrupados por status dentro de un batch.
        """
        statement = (
            select(Document.status, func.count())
            .where(Document.batch_id == batch_id)
            .group_by(Document.status)
        )

        rows = self.db.execute(statement).all()

        return {
            status.value if isinstance(status, DocumentStatus) else str(status): count
            for status, count in rows
        }