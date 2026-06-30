from pydantic import BaseModel


class MetricsRead(BaseModel):
    """
    Respuesta de metricas operativas por organizacion.

    Es una vista agregada para monitoreo basico y demo del sistema.
    """

    documents_total: int
    documents_by_status: dict[str, int]
    batches_total: int
    batches_by_status: dict[str, int]
    duplicate_candidates: int