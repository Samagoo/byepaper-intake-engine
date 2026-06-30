import uuid

from sqlalchemy.orm import Session

from app.models import Organization
from app.models.enums import BatchStatus
from app.repositories.batch_repository import BatchRepository
from app.schemas.batch import BatchCreate, BatchListResponse

class BatchNotFoundError(Exception):
    """
    Manejo de error cuando el Batch no se encuentra
    """
    pass

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

    def list_batches(
        self,
        *,
        current_organization: Organization,
        status: BatchStatus | None,
        limit: int,
        offset: int,
    ) -> BatchListResponse:
        """
        Orquesta la recuperación de una lista paginada de lotes.
        
        Combina la obtención de los registros (items) y el conteo total para 
        la construcción de una respuesta paginada completa.
        """
        items = self.batch_repository.list_for_organization(
            organization_id=current_organization.id,
            status=status,
            limit=limit,
            offset=offset,
        )

        total = self.batch_repository.count_for_organization(
            organization_id=current_organization.id,
            status=status,
        )

        return BatchListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_batch(
        self,
        *,
        current_organization: Organization,
        batch_id: uuid.UUID,
    ):
        """
        Recupera un lote específico por ID.
        
        Implementa una validación de existencia que eleva una excepción personalizada
        si el recurso no existe o no pertenece a la organización solicitante.
        """
        batch = self.batch_repository.get_by_id_for_organization(
            batch_id=batch_id,
            organization_id=current_organization.id,
        )

        if batch is None:
            # Lanzamiento de excepción de dominio para ser capturada por el middleware de errores
            raise BatchNotFoundError("Batch not found")

        return batch