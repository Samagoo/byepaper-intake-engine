from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Clase central de configuración de la aplicación. 
    Utiliza Pydantic para validar y cargar automáticamente las variables
    desde el archivo .env o el entorno del sistema
    """

    #Configuracion de Pydantic para cargar variables de entorno desde un archivo .env
    # ignore asegura que si hay variables en el .env que no están definidas en la clase, no se lanzará un error
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


    APP_NAME: str = "ByePaper Intake Engine"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str
    REDIS_URL: str
    RQ_QUEUE_NAME: str = "document-processing"

    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "/data/storage"

    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_MIME_TYPES: str = "application/pdf,image/png,image/jpeg,text/plain"

    CORS_ORIGINS: str = "http://localhost:5173"
    LOG_LEVEL: str = "INFO"

    # Secreto usado para generar hashes HMAC de API keys.
    API_KEY_HASH_SECRET: str = "change-this-secret-in-production"

    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024
    ALLOWED_UPLOAD_MIME_TYPES: str = "application/pdf,image/png,image/jpeg,text/plain"
    LOCAL_STORAGE_ROOT: str = "data/uploads"

    @property
    def allowed_mime_types(self) -> set[str]:
        """
        Convierte la cadena de texto separada por comas en un Set de Python. 
        Se usa un set porque las búsquedas son más rápidas y no permite duplicados.
        """
        return {
            mime_type.strip()
            for mime_type in self.ALLOWED_MIME_TYPES.split(",")
            if mime_type.strip()
        }

    @property
    def cors_origins(self) -> list[str]:
        """
        Convierte la cadena de texto de orígenes CORS en una lista. 
        FastAPI requiere una lista de strings para configurar el middleware
        """
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

@lru_cache
def get_settings() -> Settings:
    """
    Factory function para obtener la configuración 
    El decorador lru_cache implementa el patrón Singleton de forma nativa. 
    Garantiza que el archivo .env se lea del dicto solo una vez al arrancar
    la aplicación, y las siguientes llamadas devuelvan el objeto en memoria, 
    evitando así la sobrecarga de leer el archivo repetidamente.
    """
    return Settings()