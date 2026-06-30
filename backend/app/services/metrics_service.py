from sqlalchemy.orm import Session

from app.models import Organization
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.metrics import MetricsRead


class MetricsService:
    """
    Servicio de metricas operativas.

    Mantiene el aislamiento multi-tenant usando la organizacion autenticada.
    """

    def __init__(self, db: Session):
        self.metrics_repository = MetricsRepository(db)

    def get_metrics(
        self,
        *,
        current_organization: Organization,
    ) -> MetricsRead:
        """
        Construye las metricas principales para una organizacion.
        """
        return MetricsRead(
            documents_total=self.metrics_repository.count_documents(
                organization_id=current_organization.id,
            ),
            documents_by_status=self.metrics_repository.count_documents_by_status(
                organization_id=current_organization.id,
            ),
            batches_total=self.metrics_repository.count_batches(
                organization_id=current_organization.id,
            ),
            batches_by_status=self.metrics_repository.count_batches_by_status(
                organization_id=current_organization.id,
            ),
            duplicate_candidates=self.metrics_repository.count_duplicate_candidates(
                organization_id=current_organization.id,
            ),
        )