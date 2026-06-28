import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

#Instanciar un logger específico para las peticiones HTTP
#Al usar app.http, se puede filtrar separando los logs web de los logs internos
logger = logging.getLogger("app.http")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middelware que intercepta todas las peticiones HTTP entrantes y salientes. 

    Responsabilidades: 
    1. Asegurar que cada petición tenga un identificador único 
    2. Medir el tiempo exacto que tarda el servidor en responder
    3. Escribir un log estructurado (JSON) con los metadatos de la petición 
    """
    async def dispatch(self, request: Request, call_next):
        #1. Verificar si el cliente envió un request_id, si no lo hizo, generamos uno nuevo
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        #Guardar el ID en el estado del request para que cualquier parte del código pueda acceder a él
        request.state.request_id = request_id

        #2. Iniciar el cronómetro para medir la duración de la petición
        start_time = time.perf_counter()

        try:
            #Pasar la pelota al siguiente middleware o al endpoint final para que procese la petición
            response = await call_next(request)
        except Exception:
            #3. En caso de error, calcular la duración y loguear la excepción con los metadatos
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.exception(
                "http_request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                },
            )
            raise
        
        #Si todo salió bien, calcular la duración
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        #Agregar el request_id a la respuesta HTTP para que el cliente pueda rastrear la petición
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response