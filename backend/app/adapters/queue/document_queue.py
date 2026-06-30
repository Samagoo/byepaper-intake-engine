import uuid

from rq import Queue

from app.adapters.queue.redis_client import get_redis_client
from app.core.config import get_settings
from app.workers.document_jobs import process_document_job


class DocumentQueue:
    """
    Adapter para encolar documentos en Redis/RQ.

    La API no debe procesar documentos directamente. Solo recibe el archivo,
    guarda metadata y deja un job pendiente para que el worker trabaje en
    segundo plano.
    """

    def __init__(self):
        self.settings = get_settings()

        # RQ trabaja mejor con respuestas en bytes, por eso usamos False.
        self.redis_connection = get_redis_client(decode_responses=False)

        self.queue = Queue(
            self.settings.RQ_QUEUE_NAME,
            connection=self.redis_connection,
        )

    def enqueue_document_processing(
        self,
        *,
        document_id: uuid.UUID,
    ) -> str:
        """
        Encola el procesamiento de un documento.

        Retorna el job_id para poder rastrear el trabajo en logs o debugging.
        """
        job = self.queue.enqueue(
            process_document_job,
            str(document_id),
            job_timeout=300,
        )

        return job.id