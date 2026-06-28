from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.services.organization_service import (
    OrganizationAlreadyExistsError,
    OrganizationService,
)

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


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