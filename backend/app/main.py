from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health
from app.api.routers import organizations
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware

#Inicialización de la configuración 
settings = get_settings()
#Configuración del sistema de logging global antes de iniciar la aplicación 
configure_logging(settings.LOG_LEVEL)

#Instalación de la aplicación 
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Document intake engine for ByePaper technical challenge.",
)

#Registro del middleware para la trazabilidad de peticiones mediante Request-ID
app.add_middleware(RequestIdMiddleware)

#Configuración del middleware CROS. Permitir la comunicación entre el frontend y la API, 
#restringiendo el acceso únicamente a los orígenes autorizados
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"], #Permite los verbos HTTP
    allow_headers=["*"], #Permite todos los encabezados HTTP
)

#Inclusión de los routers definidos para la segmentación de la API
app.include_router(health.router)
# Endpoints de negocio versionados.
app.include_router(
    organizations.router,
    prefix=settings.API_V1_PREFIX,
)


@app.get("/", tags=["root"])
def root():
    """
    Endpoint raíz utilizado para la validación del servicio. 
    Proporciona información de referencia sobre las rutas de monitoreo disponible
    """
    return {
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }