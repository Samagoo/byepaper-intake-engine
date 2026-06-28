from pathlib import Path

from app.adapters.storage.base import StorageAdapter

class LocalStorageAdapter(StorageAdapter):
    """
    Implementación del adaptador de almacenamiento que utiliza el sistema de 
    archivos local. Esta clase permite guardar, leer y verificar la existencia de
    """
    def __init__(self, root_path: str):
        #Resolver la ruta absoluta para evitar ambigüedades
        self.root_path = Path(root_path).resolve()
        #Asegurarse de que el directorio raíz exista, si no, crearlo
        self.root_path.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, *, key: str, data: bytes, content_type: str) -> str:
        #Obtener la ruta validada de forma segura
        target_path = self._safe_path(key)
        #Crear carpetas anidadas si la key incluye subdirectorios
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

        return key

    def read_bytes(self, *, key: str) -> bytes:
        target_path = self._safe_path(key)
        return target_path.read_bytes()

    def exists(self, *, key: str) -> bool:
        target_path = self._safe_path(key)
        return target_path.exists()

    def _safe_path(self, key: str) -> Path:
        """
        Previene Path Traversal Attacks. Valida que la key no intente escapar del directorio root_path
        """
        #Evitar usar rutas absolutas o intentos de subir de nivel 
        if key.startswith("/") or ".." in Path(key).parts:
            raise ValueError("Invalid storage key")

        #Calcular la ruta final 
        target_path = (self.root_path / key).resolve()

        #verificar que la ruta final siga siendo hija de la carpeta raiz 
        if self.root_path != target_path and self.root_path not in target_path.parents:
            raise ValueError("Invalid storage key")

        return target_path