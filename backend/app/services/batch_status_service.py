import uuid

from sqlalchemy.orm import Session

from app.models.enums import BatchStatus, DocumentStatus
from app.repositories.batch_repository import BatchRepository
from app.repositories.document_repository import DocumentRepository


class BatchStatusService:
    """
    Servicio encargado de derivar el estado de un batch desde sus documentos.

    Regla importante del challenge:
    El batch no debe cambiarse como un switch manual. Su estado debe reflejar
    lo que esta pasando con sus documentos.
    """

    PROCESSING_STATUSES = {
        DocumentStatus.QUEUED,
        DocumentStatus.EXTRACTING,
        DocumentStatus.CLASSIFIED,
        DocumentStatus.NEEDS_REVIEW,
    }

    FINAL_SUCCESS_STATUSES = {
        DocumentStatus.APPROVED,
        DocumentStatus.REJECTED,
    }

    def __init__(self, db: Session):
        self.db = db
        self.batch_repository = BatchRepository(db)
        self.document_repository = DocumentRepository(db)

    def recalculate_for_batch(
        self,
        *,
        batch_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> BatchStatus:
        """
        Recalcula y persiste el estado del batch.

        Se filtra por organization_id para mantener aislamiento multi-tenant.
        """
        batch = self.batch_repository.get_by_id_for_organization(
            batch_id=batch_id,
            organization_id=organization_id,
        )

        if batch is None:
            raise ValueError("Batch not found")

        document_statuses = self.document_repository.list_statuses_for_batch(
            batch_id=batch.id,
        )

        next_status = self._derive_status(document_statuses)

        self.batch_repository.update_status(
            batch=batch,
            status=next_status,
        )

        return next_status

    def _derive_status(
        self,
        document_statuses: list[DocumentStatus],
    ) -> BatchStatus:
        """
        Convierte estados de documentos en estado de batch.
        """
        if not document_statuses:
            return BatchStatus.CREATED

        statuses = set(document_statuses)

        if statuses == {DocumentStatus.UPLOADED}:
            return BatchStatus.RECEIVING

        if statuses == {DocumentStatus.FAILED}:
            return BatchStatus.FAILED

        if DocumentStatus.FAILED in statuses:
            return BatchStatus.PARTIALLY_FAILED

        if statuses.issubset(self.FINAL_SUCCESS_STATUSES):
            return BatchStatus.COMPLETED

        if statuses.intersection(self.PROCESSING_STATUSES):
            return BatchStatus.PROCESSING

        return BatchStatus.PROCESSING