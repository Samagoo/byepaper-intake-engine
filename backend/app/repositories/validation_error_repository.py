import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import ValidationError as DocumentValidationError


class ValidationErrorRepository:
    """
    Repository para errores de validacion.

    Estos errores indican campos faltantes o invalidos encontrados despues de
    extraer informacion del documento.
    """

    def __init__(self, db: Session):
        self.db = db

    def delete_for_document(
        self,
        *,
        document_id: uuid.UUID,
    ) -> None:
        """
        Borra errores anteriores del documento antes de revalidar.
        """
        statement = delete(DocumentValidationError).where(
            DocumentValidationError.document_id == document_id,
        )

        self.db.execute(statement)
        self.db.flush()

    def create_many(
        self,
        *,
        document_id: uuid.UUID,
        missing_fields: list[str],
    ) -> list[DocumentValidationError]:
        """
        Crea errores de validacion para campos requeridos faltantes.
        """
        errors: list[DocumentValidationError] = []

        for key_field in missing_fields:
            error = DocumentValidationError(
                document_id=document_id,
                key_field=key_field,
                code="required_field_missing",
                message=f"Field '{key_field}' is required",
            )

            self.db.add(error)
            errors.append(error)

        self.db.flush()

        for error in errors:
            self.db.refresh(error)

        return errors