from sqlalchemy.orm import Session

from app.models import Organization
from app.repositories.batch_repository import BatchRepository
from app.schemas.batch import BatchCreate


class BatchService:
    """
    Capa de servicio para la gestión de la lógica de negocio relacionada con Batch. 
    Coordina la interacción entre los esquemas de datos y los repositorios de persistencia. 
    """
    def __init__(self, db: Session):
        self.db = db
        self.batch_repository = BatchRepository(db)

    def create_batch(
        self,
        *,
        current_organization: Organization,
        data: BatchCreate,
    ):
        """
        Gestiona la creación de un nuevo Batch dentro de una transacción atómica. 

        Aplica el patrón Unit of Work: si cualquier operación de persistencia falla,
        se ejecuta un rollback para garantizar la consistencia de los datos en PostreSQL. 
        """
        try:
            # Delegación de la lógica de creación al repositorio 
            batch = self.batch_repository.create(
                organization_id=current_organization.id,
                name=data.name,
                source=data.source,
                metadata=data.metadata,
            )
            # Confirmación de la transacción tras la ejecución exitosa 
            self.db.commit()
            return batch

        except Exception:
            # Reversión de la transacción ante cualquier excepción detectada 
            self.db.rollback()
            raise