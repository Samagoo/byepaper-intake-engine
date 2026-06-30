import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_organization
from app.models import Organization
from app.models.enums import BatchStatus
from app.schemas.batch import BatchCreate, BatchListResponse, BatchRead
from app.services.batch_service import BatchNotFoundError, BatchService

router = APIRouter(
    prefix="/batches",
    tags=["batches"],
)


@router.post(
    "",
    response_model=BatchRead,
    status_code=status.HTTP_201_CREATED,
)
def create_batch(
    payload: BatchCreate,
    # Dependencia de la seguridad: asegura que solo organizaciones autenticadas accedan
    current_organization: Organization = Depends(get_current_organization),
    # Dependencia de base de datos: provee una sesión gestionada para la transacción
    db: Session = Depends(get_db),
):
    """
    Endpoint para la creación de nuevos lotes de procesamiento. 

    Recibe los datos validados, los vincula a la organización del usuario autenticado
    y delega la ejecución de la lógica de negocio al BatchService
    """
    # Intanciación del servicio con la sesión de base de datos inyectada
    service = BatchService(db)

    # Ejecución de la operación y retorno del resultado serializado mediante BatchRead
    return service.create_batch(
        current_organization=current_organization,
        data=payload,
    )

@router.get(
    "",
    response_model=BatchListResponse,
)
def list_batches(
    # Uso de Query para validar parámetros de paginación y filtrado desde la URL
    batch_status: BatchStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Endpoint para recuperar una lista paginada de lotes.
    
    Permite filtrar por estado y soporta paginación mediante limit y offset,
    asegurando un límite máximo de 100 registros por solicitud para proteger el rendimiento.
    """
    service = BatchService(db)

    return service.list_batches(
        current_organization=current_organization,
        status=batch_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{batch_id}",
    response_model=BatchRead,
)
def get_batch(
    batch_id: uuid.UUID,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Endpoint para obtener el detalle de un lote específico.
    
    Implementa un manejo de excepciones para transformar errores de negocio 
    en respuestas HTTP 404, mejorando la semántica de la API.
    """
    service = BatchService(db)

    try:
        return service.get_batch(
            current_organization=current_organization,
            batch_id=batch_id,
        )

    except BatchNotFoundError as exc:
        # Transformación de la excepción de dominio en un error HTTP estándar
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc