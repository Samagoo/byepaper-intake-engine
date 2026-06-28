from app.adapters.storage.base import StorageAdapter
from app.adapters.storage.local import LocalStorageAdapter
from app.core.config import get_settings


def get_storage_adapter() -> StorageAdapter:
    """
    Mira el manual de configuración y decide a quién delegarle el trabajo
    """
    settings = get_settings()

    #De momento es storage local 
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageAdapter(settings.LOCAL_STORAGE_PATH)

    #Si es un storage que no se conoce o no se puede abrir 
    raise NotImplementedError(
        f"Storage backend not implemented: {settings.STORAGE_BACKEND}"
    )