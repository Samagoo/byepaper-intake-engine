import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configura el sistema de logging global de la aplicación 

    Transforma los logs tradicionales de texto plano a formato JSON.
    Esto es una práctica fundamental de Observabilidad para producción, ya que 
    permite que herramientas de monitoreo puedan indexar, filtrar y crear alertas
    basadas en los atributos del log. 
    """

    #Enviamos los logs de salida estandar para que el contenedor los pueda capturar
    handler = logging.StreamHandler(sys.stdout)

    #Definimos la estructura JSON. 
    #Al incluir variables como request_id se prepara la arquitectura para la trazabilidad
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s "
        "%(request_id)s %(method)s %(path)s %(status_code)s %(duration_ms)s"
    )

    handler.setFormatter(formatter)

    #Obtenemos el logger raíz, que intercepta todos los logs
    root_logger = logging.getLogger()
    #Limpiamos handlers previos para evitar duplicación de logs
    root_logger.handlers.clear()
    #Agregamos el handler que definimos previamente y establecemos el nivel de logging
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())