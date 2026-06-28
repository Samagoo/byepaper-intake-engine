from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    """
    Interfaz para el almacenamiento de documentos. 
    Siguiendo el principio de inversión de dependencias, los servicios de alto nivel 
    no deben depender de detalles de implementación, sino de abstracción.
    Esto permite cambiar de LogalStorage a S3Storage en producción simplemente 
    cambiando la clase instanciada, sin tocar la lógica de negocio. 
    """
    @abstractmethod
    def save_bytes(self, *, key: str, data: bytes, content_type: str) -> str:
        """
        Guarda los bytes en medio de almacenamiento y retorna la ruta o key final
        - key: identificador único del archivo 
        - data: Contenido binario del archivo 
        - content_type: Tipo MIME
        """
        raise NotImplementedError

    @abstractmethod
    def read_bytes(self, *, key: str) -> bytes:
        """Recupera los bytes del archivo almacenado dado su key"""
        raise NotImplementedError

    @abstractmethod
    def exists(self, *, key: str) -> bool:
        """Verifica si un archivo existe en el almacenamiento"""
        raise NotImplementedError