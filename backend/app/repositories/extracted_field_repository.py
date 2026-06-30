import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
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
    
    def list_for_document(
        self,
        *,
        document_id: uuid.UUID,
    ) -> list[ExtractedField]:
        """
        Lista los campos extraidos de un documento.
        """
        from sqlalchemy import select

        statement = (
            select(ExtractedField)
            .where(ExtractedField.document_id == document_id)
            .order_by(ExtractedField.created_at.asc())
        )

        return list(self.db.execute(statement).scalars().all())
    
    def upsert_human_fields(
        self,
        *,
        document_id: uuid.UUID,
        fields: dict[str, str],
        reviewer_id: str | None,
    ) -> list[ExtractedField]:
        """
        Crea o actualiza campos corregidos por un humano.

        Si el campo ya existe, se actualiza.
        Si no existe, se crea.
        """
        updated_fields: list[ExtractedField] = []

        for key_field, value in fields.items():
            statement = select(ExtractedField).where(
                ExtractedField.document_id == document_id,
                ExtractedField.key_field == key_field,
            )

            field = self.db.execute(statement).scalar_one_or_none()

            if field is None:
                field = ExtractedField(
                    document_id=document_id,
                    key_field=key_field,
                    value=value,
                    confidence_score=1.0,
                    source=FieldSource.HUMAN,
                    corrected_by=reviewer_id,
                    corrected_at=datetime.now(timezone.utc),
                )
                self.db.add(field)
            else:
                field.value = value
                field.confidence_score = 1.0
                field.source = FieldSource.HUMAN
                field.corrected_by = reviewer_id
                field.corrected_at = datetime.now(timezone.utc)

            updated_fields.append(field)

        self.db.flush()

        for field in updated_fields:
            self.db.refresh(field)

        return updated_fields