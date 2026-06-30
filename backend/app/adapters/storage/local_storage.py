from pathlib import Path
from app.core.config import get_settings

class LocalStorageAdapter:
    """
    Adaptador de almacenamiento para el sistema de archivos local.
    Implementa la persistencia de bytes en disco utilizando rutas abstraídas.
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
        Persiste el contenido binario en la ruta definida por el storage_key.
        
        Asegura la existencia de la jerarquía de directorios necesaria antes de la escritura,
        garantizando la resiliencia operativa ante rutas inexistentes.
        """
        # Unión de ruta segura utilizando el operador '/' de pathlib
        file_path = self.storage_root / storage_key
        
        # Creación recursiva del directorio padre (mkdir -p)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Escritura atómica de bytes
        file_path.write_bytes(content)