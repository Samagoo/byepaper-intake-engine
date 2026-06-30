import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import EventLog
from app.models.enums import ActorType


class EventLogRepository:
    """
    Repository para auditoria.

    Cada transicion importante del documento debe dejar una huella.
    Esto permite reconstruir la historia del procesamiento.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        event_type: str,
        actor_type: ActorType,
        actor_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventLog:
        """
        Crea un evento de auditoria para una entidad del sistema.
        """
        event = EventLog(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload or {},
        )

        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)

        return event