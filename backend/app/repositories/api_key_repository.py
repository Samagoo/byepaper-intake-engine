import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey


class ApiKeyRepository:
    """
    Encapsula operaciones de base de datos relacionadas con API keys.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        key_hash: str,
        prefix: str,
    ) -> ApiKey:
        # Creamos el registro con hash, jamás con la API key real.
        api_key = ApiKey(
            organization_id=organization_id,
            key_hash=key_hash,
            prefix=prefix,
        )

        self.db.add(api_key)
        self.db.flush()
        self.db.refresh(api_key)

        return api_key

    def get_active_by_prefix(self, prefix: str) -> list[ApiKey]:
        """
        Busca API keys activas por prefix.
        """
        statement = select(ApiKey).where(
            ApiKey.prefix == prefix,
            ApiKey.revoked_at.is_(None),
        )

        return list(self.db.execute(statement).scalars().all())