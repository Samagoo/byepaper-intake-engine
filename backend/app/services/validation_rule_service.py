import uuid

from sqlalchemy.orm import Session

from app.models import Organization
from app.repositories.validation_rule_repository import ValidationRuleRepository
from app.schemas.validation_rule import ValidationRuleUpsert


class OrganizationMismatchError(Exception):
    """
    Se lanza cuando una API key intenta modificar reglas de otra organizacion.
    """


class ValidationRuleService:
    """
    Servicio para administrar reglas de validacion por organizacion.
    """

    def __init__(self, db: Session):
        self.db = db
        self.validation_rule_repository = ValidationRuleRepository(db)

    def upsert_rule(
        self,
        *,
        current_organization: Organization,
        organization_id: uuid.UUID,
        data: ValidationRuleUpsert,
    ):
        """
        Crea o actualiza la regla del tipo documental indicado.

        La organization_id de la URL debe coincidir con la organizacion
        autenticada por API key.
        """
        if current_organization.id != organization_id:
            raise OrganizationMismatchError("Organization not found")

        try:
            rule = self.validation_rule_repository.upsert(
                organization_id=current_organization.id,
                document_type=data.document_type,
                required_fields=data.required_fields,
            )

            self.db.commit()
            return rule

        except Exception:
            self.db.rollback()
            raise