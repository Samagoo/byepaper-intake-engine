from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.adapters.hashing.api_key_hasher import ApiKeyHasher
from app.core.database import get_db
from app.models import Organization
from app.models.enums import OrganizationStatus
from app.repositories.api_key_repository import ApiKeyRepository


# Header donde espera recibir la API key.
# El cliente deberá mandar:
# X-API-Key: byp_xxxxx_xxxxx
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def get_current_organization(
    raw_api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> Organization:
    """
    Valida la API key enviada por el cliente y devuelve la organización autenticada.

    Esta dependencia será usada por endpoints protegidos.

    Reglas:
    - Si no hay API key, responder 401.
    - Si el formato es inválido, responder 401.
    - Si el hash no coincide, responder 401.
    - Si la organización está inactiva, responder 403.
    """
    if raw_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    api_key_hasher = ApiKeyHasher()
    prefix = api_key_hasher.extract_prefix(raw_api_key)

    if prefix is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    api_key_repository = ApiKeyRepository(db)
    candidate_api_keys = api_key_repository.get_active_by_prefix(prefix)

    for api_key in candidate_api_keys:
        is_valid = api_key_hasher.verify_api_key(
            raw_api_key=raw_api_key,
            stored_hash=api_key.key_hash,
        )

        if not is_valid:
            continue

        organization = api_key.organization

        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        if organization.status != OrganizationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization is inactive",
            )

        return organization

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )