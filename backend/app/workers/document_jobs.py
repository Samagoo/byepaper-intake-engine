import logging
import uuid

from app.core.database import SessionLocal
from app.services.document_processing_service import DocumentProcessingService

logger = logging.getLogger("app.worker.document_jobs")


def process_document_job(document_id: str) -> None:
    """
    Job de procesamiento de documento.

    Este es el punto de entrada del worker. RQ ejecuta esta funcion en un
    proceso separado de FastAPI.
    """
    parsed_document_id = uuid.UUID(document_id)
    db = SessionLocal()

    try:
        logger.info(
            "document_job_started",
            extra={"document_id": document_id},
        )

        service = DocumentProcessingService(db)
        service.process_document(document_id=parsed_document_id)

        logger.info(
            "document_job_finished",
            extra={"document_id": document_id},
        )

    finally:
        db.close()