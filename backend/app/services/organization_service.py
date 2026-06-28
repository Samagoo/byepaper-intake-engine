from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import OrganizationCreate


class OrganizationAlreadyExistsError(Exception):
    """
    Error de dominio.

    Cuando se intenta crear una organización
    con un slug que ya existe.
    """


class OrganizationService:
    """
    Contiene reglas de negocio relacionadas con organizaciones.

    El endpoint no debe decidir reglas importantes.
    El repository no debe decidir reglas de negocio.
    Esta capa vive en medio.
    """

    def __init__(self, db: Session):
        self.db = db
        self.organization_repository = OrganizationRepository(db)

    def create_organization(self, data: OrganizationCreate):
        existing_organization = self.organization_repository.get_by_slug(
            data.slug
        )

        if existing_organization is not None:
            raise OrganizationAlreadyExistsError(
                f"Organization with slug '{data.slug}' already exists"
            )

        try:
            organization = self.organization_repository.create(
                name=data.name,
                slug=data.slug,
                status=data.status,
            )

            # Confirmamos la transacción.
            self.db.commit()

            return organization

        except IntegrityError as exc:
            # Si dos requests intentan crear el mismo slug al mismo tiempo,
            # PostgreSQL protege con el índice único.
            self.db.rollback()

            raise OrganizationAlreadyExistsError(
                f"Organization with slug '{data.slug}' already exists"
            ) from exc

        except Exception:
            # Ante cualquier error inesperado, regresamos la transacción.
            self.db.rollback()
            raise