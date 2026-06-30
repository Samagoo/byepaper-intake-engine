import hashlib

from fastapi import HTTPException, Request, status

from app.adapters.queue.redis_client import get_redis_client
from app.core.config import get_settings


class ApiKeyRateLimiter:
    """
    Rate limiter simple por API key usando Redis.

    Protege al backend de clientes que envian demasiadas peticiones en una
    ventana corta de tiempo.
    """

    def __init__(self):
        self.settings = get_settings()
        self.redis_client = get_redis_client(decode_responses=True)

    def check(
        self,
        *,
        raw_api_key: str | None,
    ) -> None:
        """
        Incrementa contador por API key y bloquea si supera el limite.

        Nunca guardamos la API key real como llave de Redis. Usamos SHA-256
        para no exponer secretos en la infraestructura.
        """
        if not self.settings.RATE_LIMIT_ENABLED:
            return

        if raw_api_key is None:
            return

        api_key_hash = hashlib.sha256(
            raw_api_key.encode("utf-8")
        ).hexdigest()

        redis_key = f"rate-limit:api-key:{api_key_hash}"

        current_count = self.redis_client.incr(redis_key)

        if current_count == 1:
            self.redis_client.expire(
                redis_key,
                self.settings.RATE_LIMIT_WINDOW_SECONDS,
            )

        if current_count > self.settings.RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )


rate_limiter = ApiKeyRateLimiter()


async def rate_limit_by_api_key(request: Request) -> None:
    """
    Dependencia de FastAPI para aplicar rate limiting.

    Lee X-API-Key directamente del request. La autenticacion real sigue viviendo
    en get_current_organization.
    """
    raw_api_key = request.headers.get("X-API-Key")

    rate_limiter.check(
        raw_api_key=raw_api_key,
    )