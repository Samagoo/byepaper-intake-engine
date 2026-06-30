import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ValidationRule
from app.models.enums import DocumentType


class ValidationRuleRepository:
    """
    Repository para reglas de validacion por organizacion.

    Si existe una regla en DB, se usa. Si no existe, el pipeline puede usar
    reglas default para mantener el flujo funcionando.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_for_organization_and_type(
        self,
        *,
        organization_id: uuid.UUID,
        document_type: DocumentType,
    ) -> ValidationRule | None:
        """
        Busca reglas por organization_id + document_type.
        """
        statement = select(ValidationRule).where(
            ValidationRule.organization_id == organization_id,
            ValidationRule.document_type == document_type,
        )

        return self.db.execute(statement).scalar_one_or_none()