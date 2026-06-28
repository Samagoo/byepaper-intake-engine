import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization
from app.models.enums import OrganizationStatus


class OrganizationRepository:
    """
    Encapsula las consultas de base de datos relacionadas con organizaciones.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        # Busca una organización por ID.
        statement = select(Organization).where(
            Organization.id == organization_id
        )

        return self.db.execute(statement).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Organization | None:
        # Busca una organización por slug.
        # El slug debe ser único.
        statement = select(Organization).where(
            Organization.slug == slug
        )

        return self.db.execute(statement).scalar_one_or_none()

    def create(
        self,
        *,
        name: str,
        slug: str,
        status: OrganizationStatus,
    ) -> Organization:
        # Crea una instancia ORM.
        organization = Organization(
            name=name,
            slug=slug,
            status=status,
        )

        # La agregamos a la sesión.
        # Todavía no se guarda definitivamente hasta hacer commit.
        self.db.add(organization)

        # flush manda el INSERT a PostgreSQL sin cerrar la transacción.
        # Esto permite obtener el id generado antes del commit.
        self.db.flush()

        # refresh trae desde DB los valores generados automáticamente,
        # como created_at y updated_at.
        self.db.refresh(organization)

        return organization