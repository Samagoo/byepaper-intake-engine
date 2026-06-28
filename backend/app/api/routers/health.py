from fastapi import APIRouter, HTTPException, status

from app.adapters.queue.redis_client import check_redis_connection
from app.core.config import get_settings
from app.core.database import check_database_connection

#El router define los endpoints de monitoreo. 
router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """
    Endpoint de 'Liveness Probe'. 
    Indica que el proceso de la aplicación está activo y respondiendo peticiones
    HTTP básicas. No verifica dependencias externas. 
    """
    settings = get_settings()

    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready")
def ready():
    """
    Endpoint de 'Readiness Probe'. 
    Verifica la conectividad con los servicios críticos. Si alguna de estas dependencias 
    no responde, el servicio se marca como no disponible, evitando que el tráfico 
    sea enviado a una instancia que no puede procesar operaciones. 
    """
    checks = {
        "database": False,
        "redis": False,
    }

    #Validación de conectividad a PostgreSQL
    try:
        checks["database"] = check_database_connection()
    except Exception:
        checks["database"] = False

    #Validación de conectividad a Redis
    try:
        checks["redis"] = check_redis_connection()
    except Exception:
        checks["redis"] = False

    #Si algún servicio falla, se retorna a 503. 
    if not all(checks.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "checks": checks,
            },
        )

    return {
        "status": "ready",
        "checks": checks,
    }