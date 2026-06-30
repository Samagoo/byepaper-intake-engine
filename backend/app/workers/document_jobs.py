import logging
import uuid

from app.core.database import SessionLocal
from app.models import Document
from app.models.enums import DocumentStatus

logger = logging.getLogger("app.worker.document_jobs")


def process_document_job(document_id: str) -> None:
    """
    Job inicial de procesamiento de documento.

    En esta fase todavía no hacemos extracción/clasificación real. Solo dejamos
    conectado el camino API -> Redis/RQ -> Worker -> PostgreSQL.

    En la siguiente fase este job será el punto de entrada del pipeline:
    extracting -> classified -> needs_review/failed.
    """
    parsed_document_id = uuid.UUID(document_id)

    db = SessionLocal()

    try:
        document = db.get(Document, parsed_document_id)

        if document is None:
            logger.warning(
                "document_not_found",
                extra={"document_id": document_id},
            )
            return

        if document.status != DocumentStatus.QUEUED:
            logger.info(
                "document_skipped_unexpected_status",
                extra={
                    "document_id": document_id,
                    "status": document.status,
                },
            )
            return

        logger.info(
            "document_job_received",
            extra={"document_id": document_id},
        )

        # Marcamos que el worker sí tomó el documento.
        # El pipeline completo se implementará en la siguiente fase.
        document.status = DocumentStatus.EXTRACTING

        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "document_job_failed",
            extra={"document_id": document_id},
        )
        raise

    finally:
        db.close()