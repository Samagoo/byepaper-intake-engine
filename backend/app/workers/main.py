import logging

from redis import Redis
from rq import Queue, Worker

from app.core.config import get_settings
from app.core.logging import configure_logging


def main() -> None:
    """
    Punto de entrada del proceso Worker
    Se ejecuta de forma aislada a la API. Su función es escuchar constantemente
    la cola de Redis y ejecutar jobs de procesamiento de documentos asíncrona. 
    """
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    logger = logging.getLogger("app.worker")

    #Establecemos conexión con el broker de mensajes
    redis_connection = Redis.from_url(settings.REDIS_URL)
    #Verificamos la conectividad antes de intentar iniciar el worker
    redis_connection.ping()

    #Instanciamos la cola de trabajos definida en las variables de entorno
    queue = Queue(
        settings.RQ_QUEUE_NAME,
        connection=redis_connection,
    )

    #El worker se suscribe a la cola para procesar los jobs 
    worker = Worker(
        [queue],
        connection=redis_connection,
    )

    logger.info(
        "worker_started",
        extra={
            "queue": settings.RQ_QUEUE_NAME,
        },
    )

    #Iniciamos el ciclo de trabajo. El proceso se mantendrá vivo esuchando 
    #eventos hasta que sea detenido manualmente 
    worker.work()


if __name__ == "__main__":
    main()