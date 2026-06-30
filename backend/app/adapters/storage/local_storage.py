from pathlib import Path

from app.core.config import get_settings


class LocalStorageAdapter:
    """
    Adapter de almacenamiento local.

    Esta clase encapsula el acceso al sistema de archivos. El resto del
    sistema no debe conocer rutas absolutas ni detalles del disco.
    """

    def __init__(self):
        self.settings = get_settings()
        self.storage_root = Path(self.settings.LOCAL_STORAGE_ROOT)

    def save(
        self,
        *,
        storage_key: str,
        content: bytes,
    ) -> None:
        """
        Guarda bytes en disco usando una storage_key relativa.

        La DB solo guarda storage_key, no una ruta absoluta del servidor.
        """
        file_path = self.storage_root / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

    def read(
        self,
        *,
        storage_key: str,
    ) -> bytes:
        """
        Lee bytes desde storage local.

        El worker usa este metodo para recuperar el archivo que la API
        guardo durante el upload.
        """
        file_path = self.storage_root / storage_key
        return file_path.read_bytes()