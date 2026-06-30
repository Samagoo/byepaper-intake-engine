import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Batch
from app.models.enums import BatchStatus


class BatchRepository:
    """
    Repositorio encargado de la persistencia y recuperación de entidades Batch.
    Abstrae la lógica de acceso a datos utilizando SQLAlchemy ORM. 
    """
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
        source: str,
        metadata: dict,
    ) -> Batch:
        """
        Persiste una nueva instancia de Batch en la base de datos. 

        Utiliza flush para sincronizar el estado del objeto sin finalizar la transacción, 
        y el refresh para actualizar la instancia de los valores generados por la BD
        """
        batch = Batch(
            organization_id=organization_id,
            name=name,
            source=source,
            status=BatchStatus.CREATED,
            metadata_=metadata,
        )

        self.db.add(batch)
        self.db.flush()
        self.db.refresh(batch)

        return batch

    def get_by_id_for_organization(
        self,
        *,
        batch_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Batch | None:
        """
        Recupera un batch específico asegurando la integridad del multi-tenancy.

        Aplica un filtro compuesto para garantizar que la entidad pertenezca a la
        organización solicitada, evitando fugas de información entre organizaciones. 
        """
        statement = select(Batch).where(
            Batch.id == batch_id,
            Batch.organization_id == organization_id,
        )

        return self.db.execute(statement).scalar_one_or_none()