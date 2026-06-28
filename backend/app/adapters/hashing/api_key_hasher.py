import hashlib
import hmac
import secrets

from app.core.config import get_settings


class ApiKeyHasher:
    """
    Encapsula la generación y hashing de API keys.

    La API key real se muestra una sola vez al crearla.
    En base de datos solo se guarda el hash.
    """

    def __init__(self):
        self.settings = get_settings()

    def generate_api_key(self) -> tuple[str, str, str]:
        """
        Genera una API key nueva.

        Retorna:
        - full_api_key: la llave completa que verá el usuario una sola vez
        - prefix: identificador corto para búsqueda y debugging
        - key_hash: hash seguro para guardar en base de datos
        """
        prefix = secrets.token_hex(6)
        secret_part = secrets.token_urlsafe(32)

        full_api_key = f"byp_{prefix}_{secret_part}"
        key_hash = self.hash_api_key(full_api_key)

        return full_api_key, prefix, key_hash

    def hash_api_key(self, api_key: str) -> str:
        """
        Genera un hash HMAC-SHA256.

        Se usa HMAC con un secreto del servidor para evitar guardar
        hashes simples de las API keys.
        """
        secret = self.settings.API_KEY_HASH_SECRET.encode("utf-8")
        message = api_key.encode("utf-8")

        return hmac.new(
            secret,
            message,
            hashlib.sha256,
        ).hexdigest()

    def verify_api_key(self, *, raw_api_key: str, stored_hash: str) -> bool:
        """
        Compara la API key enviada por el cliente contra el hash guardado.

        compare_digest evita comparaciones inseguras por tiempo.
        """
        candidate_hash = self.hash_api_key(raw_api_key)

        return hmac.compare_digest(candidate_hash, stored_hash)

    def extract_prefix(self, api_key: str) -> str | None:
        """
        Extrae el prefix desde una key con formato:

        byp_<prefix>_<secret>

        El prefix ayuda a buscar candidatos en base de datos sin guardar
        ni exponer la API key completa.
        """
        parts = api_key.split("_", 2)

        if len(parts) != 3:
            return None

        key_marker, prefix, _secret = parts

        if key_marker != "byp":
            return None

        return prefix