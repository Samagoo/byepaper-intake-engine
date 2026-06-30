import uuid

from sqlalchemy import func, select
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
    
    def list_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        status: BatchStatus | None,
        limit: int,
        offset: int,
    ) -> list[Batch]:
        """
        Recupera una lista paginada de entidades Batch para una organización 
        específica filtrada opcionalmente por estado 

        Aplica un ordenamiento descendente por created_at para representar 
        los registros más recientes primero 
        """
        statement = select(Batch).where(
            Batch.organization_id == organization_id,
        )

        # Aplicación condicional de filtros 
        if status is not None:
            statement = statement.where(Batch.status == status)

        # Configuracion de paginacion y ordenamiento 
        statement = (
            statement.order_by(Batch.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.execute(statement).scalars().all())

    def count_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        status: BatchStatus | None,
    ) -> int:
        """
        Calcula el número total de registros Batch que ucmplen con los criterios
        de filtro, utilizados para la construcción de metadatos de paginación 
        """
        statement = select(func.count()).select_from(Batch).where(
            Batch.organization_id == organization_id,
        )

        if status is not None:
            statement = statement.where(Batch.status == status)

        return self.db.execute(statement).scalar_one()