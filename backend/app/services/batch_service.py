import uuid

from sqlalchemy.orm import Session

from app.models import Organization
from app.models.enums import BatchStatus, DocumentStatus

from app.repositories.batch_repository import BatchRepository
from app.repositories.document_repository import DocumentRepository

from app.schemas.batch import BatchCreate, BatchListResponse, BatchProgressRead

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
        self.document_repository = DocumentRepository(db)

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
    
    def get_batch_progress(
        self,
        *,
        current_organization: Organization,
        batch_id: uuid.UUID,
    ) -> BatchProgressRead:
        """
        Calcula progreso de un batch para polling controlado.

        Solo cuenta documentos del batch perteneciente a la organizacion
        autenticada.
        """
        batch = self.batch_repository.get_by_id_for_organization(
            batch_id=batch_id,
            organization_id=current_organization.id,
        )

        if batch is None:
            raise BatchNotFoundError("Batch not found")

        counts_by_status = self.document_repository.count_by_status_for_batch(
            batch_id=batch.id,
        )

        total_documents = sum(counts_by_status.values())

        final_count = sum(
            counts_by_status.get(status.value, 0)
            for status in {
                DocumentStatus.APPROVED,
                DocumentStatus.REJECTED,
                DocumentStatus.FAILED,
            }
        )

        progress_percent = (
            round((final_count / total_documents) * 100, 2)
            if total_documents > 0
            else 0.0
        )

        return BatchProgressRead(
            batch_id=batch.id,
            status=batch.status,
            total_documents=total_documents,
            counts_by_status=counts_by_status,
            progress_percent=progress_percent,
        )