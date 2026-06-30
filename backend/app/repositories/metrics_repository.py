import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Batch, Document
from app.models.enums import BatchStatus, DocumentStatus


class MetricsRepository:
    """
    Repository para metricas operativas.

    Estas consultas agregan informacion del sistema sin exponer datos de otras
    organizaciones.
    """

    def __init__(self, db: Session):
        self.db = db

    def count_documents(
        self,
        *,
        organization_id: uuid.UUID,
    ) -> int:
        """
        Cuenta documentos totales de una organizacion.
        """
        statement = select(func.count()).select_from(Document).where(
            Document.organization_id == organization_id,
        )

        return self.db.execute(statement).scalar_one()

    def count_documents_by_status(
        self,
        *,
        organization_id: uuid.UUID,
    ) -> dict[str, int]:
        """
        Cuenta documentos agrupados por status.
        """
        statement = (
            select(Document.status, func.count())
            .where(Document.organization_id == organization_id)
            .group_by(Document.status)
        )

        rows = self.db.execute(statement).all()

        return {
            status.value if isinstance(status, DocumentStatus) else str(status): count
            for status, count in rows
        }

    def count_batches(
        self,
        *,
        organization_id: uuid.UUID,
    ) -> int:
        """
        Cuenta batches totales de una organizacion.
        """
        statement = select(func.count()).select_from(Batch).where(
            Batch.organization_id == organization_id,
        )

        return self.db.execute(statement).scalar_one()

    def count_batches_by_status(
        self,
        *,
        organization_id: uuid.UUID,
    ) -> dict[str, int]:
        """
        Cuenta batches agrupados por status.
        """
        statement = (
            select(Batch.status, func.count())
            .where(Batch.organization_id == organization_id)
            .group_by(Batch.status)
        )

        rows = self.db.execute(statement).all()

        return {
            status.value if isinstance(status, BatchStatus) else str(status): count
            for status, count in rows
        }

    def count_duplicate_candidates(
        self,
        *,
        organization_id: uuid.UUID,
    ) -> int:
        """
        Cuenta documentos marcados como duplicados candidatos.
        """
        statement = select(func.count()).select_from(Document).where(
            Document.organization_id == organization_id,
            Document.is_duplicate_candidate.is_(True),
        )

        return self.db.execute(statement).scalar_one()