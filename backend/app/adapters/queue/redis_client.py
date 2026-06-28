from redis import Redis

from app.core.config import get_settings

settings = get_settings()


def get_redis_client(decode_responses: bool = True) -> Redis:
    """
    Crea y devuelve una conexión al servidor de Redis. 

    Esta función actuará como la puerta de enlace para encolar jobs de 
    procesamiento de documentos.
    """
    return Redis.from_url(
        settings.REDIS_URL,
        #Si response es True, Redis convertirá los bytes a str. Evita 
        #tener que hacer .decode() en cada respuesta.
        decode_responses=decode_responses,
    )


def check_redis_connection() -> bool:
    """
    Realiza un ping al servidor de Redis para confirmar que está vivo.
    Si redis se cae, el worker no podrá recibir documentos, por lo que la API 
    debe reportarlo como un estado fallido. 
    """
    client = get_redis_client()
    return bool(client.ping())