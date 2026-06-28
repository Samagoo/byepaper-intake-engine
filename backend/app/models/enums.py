from enum import Enum

# Gestión multi-tenant 
class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

# Control de flujo batch 
class BatchStatus(str, Enum):
    CREATED = "created"
    RECEIVING = "receiving"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_FAILED = "partially_failed"
    FAILED = "failed"

# Estado del documento 
class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CLASSIFIED = "classified"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"

# Clasificación del documento 
class DocumentType(str, Enum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    ID_DOCUMENT = "id_document"
    BANK_STATEMENT = "bank_statement"
    OTHER = "other"

# Auditoría de datos
class FieldSource(str, Enum):
    SYSTEM = "system" # OCR o extracción automática 
    HUMAN = "human" # Valor corregido por el usuario

# Trazabilidad de actores 
class ActorType(str, Enum):
    SYSTEM = "system"
    API = "api"
    REVIEWER = "reviewer"
    WORKER = "worker"