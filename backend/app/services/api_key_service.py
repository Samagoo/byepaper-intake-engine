import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.hashing.api_key_hasher import ApiKeyHasher
from app.models.enums import OrganizationStatus
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.api_key import ApiKeyCreateResponse


class OrganizationNotFoundError(Exception):
    """
    Error de dominio para organización inexistente.
    """


class OrganizationInactiveError(Exception):
    """
    Error de dominio para organización inactiva.
    """


class ApiKeyCreationError(Exception):
    """
    Error de dominio para fallos al crear API keys.
    """


class ApiKeyService:
    """
    Contiene reglas de negocio para generar API keys.

    Responsabilidades:
    - Verificar que la organización exista
    - Verificar que esté activa
    - Generar API key segura
    - Guardar solo el hash
    - Devolver la key real una sola vez
    """

    def __init__(self, db: Session):
        self.db = db
        self.organization_repository = OrganizationRepository(db)
        self.api_key_repository = ApiKeyRepository(db)
        self.api_key_hasher = ApiKeyHasher()

    def create_api_key(
        self,
        *,
        organization_id: uuid.UUID,
    ) -> ApiKeyCreateResponse:
        organization = self.organization_repository.get_by_id(
            organization_id
        )

        if organization is None:
            raise OrganizationNotFoundError(
                "Organization not found"
            )

        if organization.status != OrganizationStatus.ACTIVE:
            raise OrganizationInactiveError(
                "Organization is inactive"
            )

        # Reintentar por si existiera una colisión ultra improbable
        # de prefix o hash.
        for _ in range(3):
            full_api_key, prefix, key_hash = (
                self.api_key_hasher.generate_api_key()
            )

            try:
                api_key = self.api_key_repository.create(
                    organization_id=organization.id,
                    key_hash=key_hash,
                    prefix=prefix,
                )

                self.db.commit()

                return ApiKeyCreateResponse(
                    id=api_key.id,
                    organization_id=api_key.organization_id,
                    prefix=api_key.prefix,
                    api_key=full_api_key,
                    created_at=api_key.created_at,
                )

            except IntegrityError:
                self.db.rollback()

        raise ApiKeyCreationError(
            "Could not create API key after multiple attempts"
        )