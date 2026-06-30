from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.services.organization_service import (
    OrganizationAlreadyExistsError,
    OrganizationService,
)

import uuid
from app.schemas.api_key import ApiKeyCreateResponse
from app.services.api_key_service import (
    ApiKeyCreationError,
    ApiKeyService,
    OrganizationInactiveError,
    OrganizationNotFoundError,
)

from app.core.security import get_current_organization
from app.models import Organization
from app.schemas.validation_rule import ValidationRuleRead, ValidationRuleUpsert
from app.services.validation_rule_service import (
    OrganizationMismatchError,
    ValidationRuleService,
)

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)

@router.get(
    "/me",
    response_model=OrganizationRead,
)
def get_my_organization(
    current_organization: Organization = Depends(get_current_organization),
):
    """
    Devuelve la organización asociada a la API key enviada.

    Este endpoint prueba la autenticación multi-tenant.
    El cliente no manda organization_id; el backend lo obtiene desde la API key.
    """
    return current_organization

@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
):
    """
    Crea una nueva organización.

    Esta organización será la raíz del multi-tenant.
    Después se genera una API key asociada a ella.
    """
    service = OrganizationService(db)

    try:
        return service.create_organization(payload)

    except OrganizationAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    
@router.post(
    "/{organization_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Genera una API key para una organización.

    Importante:
    - La API key completa se devuelve una sola vez.
    - En base de datos solo se guarda el hash.
    - El prefix sí se guarda para poder identificar candidatos.
    """
    service = ApiKeyService(db)

    try:
        return service.create_api_key(
            organization_id=organization_id,
        )

    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except OrganizationInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ApiKeyCreationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    
@router.put(
    "/{organization_id}/validation-rules",
    response_model=ValidationRuleRead,
)
def upsert_validation_rule(
    organization_id: uuid.UUID,
    payload: ValidationRuleUpsert,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Crea o actualiza reglas de validacion para la organizacion autenticada.
    """
    service = ValidationRuleService(db)

    try:
        return service.upsert_rule(
            current_organization=current_organization,
            organization_id=organization_id,
            data=payload,
        )

    except OrganizationMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc