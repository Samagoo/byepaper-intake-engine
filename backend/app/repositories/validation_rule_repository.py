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
    
    def upsert(
        self,
        *,
        organization_id: uuid.UUID,
        document_type: DocumentType,
        required_fields: list[str],
    ) -> ValidationRule:
        """
        Crea o actualiza una regla de validacion.

        Si ya existe una regla para organization_id + document_type,
        solo actualiza required_fields.
        """
        rule = self.get_for_organization_and_type(
            organization_id=organization_id,
            document_type=document_type,
        )

        if rule is None:
            rule = ValidationRule(
                organization_id=organization_id,
                document_type=document_type,
                required_fields=required_fields,
            )
            self.db.add(rule)
        else:
            rule.required_fields = required_fields

        self.db.flush()
        self.db.refresh(rule)

        return rule