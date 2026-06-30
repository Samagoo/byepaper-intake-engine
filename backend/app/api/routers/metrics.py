from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_organization
from app.models import Organization
from app.schemas.metrics import MetricsRead
from app.services.metrics_service import MetricsService

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
)


@router.get(
    "",
    response_model=MetricsRead,
)
def get_metrics(
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Devuelve metricas operativas agregadas para la organizacion autenticada.
    """
    service = MetricsService(db)

    return service.get_metrics(
        current_organization=current_organization,
    )