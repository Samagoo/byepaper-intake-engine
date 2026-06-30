import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi import File, Form, UploadFile

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_organization
from app.core.rate_limit import rate_limit_by_api_key

from app.models import Organization
from app.models.enums import BatchStatus

from app.schemas.batch import BatchCreate, BatchListResponse, BatchRead
from app.schemas.document import DocumentRead

from app.services.batch_service import BatchNotFoundError, BatchService
from app.services.document_service import (
    BatchNotFoundForUploadError,
    DocumentService,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidFileTypeError,
    IdempotencyConflictError,
)

router = APIRouter(
    prefix="/batches",
    tags=["batches"],
    dependencies=[Depends(rate_limit_by_api_key)],
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
    
@router.post(
    "/{batch_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_to_batch(
    batch_id: uuid.UUID,
    file: UploadFile = File(...),
    source_reference: str | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Sube un documento al batch autenticado por API key.

    La organización no llega en el body. Sale de get_current_organization,
    lo cual evita que un tenant suba archivos en batches ajenos.
    """
    service = DocumentService(db)

    try:
        return await service.upload_document(
            current_organization=current_organization,
            batch_id=batch_id,
            file=file,
            source_reference=source_reference,
            idempotency_key=idempotency_key,
        )

    except BatchNotFoundForUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc

    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc