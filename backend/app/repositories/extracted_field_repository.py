import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import ExtractedField
from app.models.enums import FieldSource


class ExtractedFieldRepository:
    """
    Repository para campos extraidos.

    Un campo extraido representa informacion encontrada o simulada por el
    pipeline: total, currency, vendor, person_name, etc.
    """

    def __init__(self, db: Session):
        self.db = db

    def delete_for_document(
        self,
        *,
        document_id: uuid.UUID,
    ) -> None:
        """
        Borra campos previos del documento.

        Esto hace que el procesamiento sea mas seguro si luego se implementa
        retry, porque evita duplicar key_field.
        """
        statement = delete(ExtractedField).where(
            ExtractedField.document_id == document_id,
        )

        self.db.execute(statement)
        self.db.flush()

    def create_many(
        self,
        *,
        document_id: uuid.UUID,
        fields: dict[str, str],
        confidence_score: float,
    ) -> list[ExtractedField]:
        """
        Crea varios campos extraidos para un documento.
        """
        created_fields: list[ExtractedField] = []

        for key_field, value in fields.items():
            field = ExtractedField(
                document_id=document_id,
                key_field=key_field,
                value=value,
                confidence_score=confidence_score,
                source=FieldSource.SYSTEM,
            )

            self.db.add(field)
            created_fields.append(field)

        self.db.flush()

        for field in created_fields:
            self.db.refresh(field)

        return created_fields