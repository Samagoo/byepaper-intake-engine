import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IdempotencyRecord


class IdempotencyRepository:
    """
    Encapsula las consultas de idempotencia.

    La idempotencia sirve para que un retry de la misma petición no cree
    documentos duplicados ni dispare efectos secundarios dos veces.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_key(
        self,
        *,
        organization_id: uuid.UUID,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        """
        Busca una petición previa usando organization_id + Idempotency-Key.

        La key solo es única dentro de una organización, no globalmente.
        """
        statement = select(IdempotencyRecord).where(
            IdempotencyRecord.organization_id == organization_id,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )

        return self.db.execute(statement).scalar_one_or_none()

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        idempotency_key: str,
        request_hash: str,
        response_snapshot: dict,
    ) -> IdempotencyRecord:
        """
        Guarda el resultado estable de una petición.

        Si el cliente repite exactamente la misma petición con la misma key,
        devolveremos response_snapshot sin crear otro documento.
        """
        record = IdempotencyRecord(
            organization_id=organization_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            response_snapshot=response_snapshot,
        )

        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)

        return record