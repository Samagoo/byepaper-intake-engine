from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_organization
from app.models import Organization
from app.schemas.batch import BatchCreate, BatchRead
from app.services.batch_service import BatchService

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