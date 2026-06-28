import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApiKeyCreateResponse(BaseModel):
    """
    Respuesta al crear una API key.

    api_key se devuelve una sola vez.
    No existe endpoint para recuperarla después.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    prefix: str
    api_key: str
    created_at: datetime