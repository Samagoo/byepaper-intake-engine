import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_organization
from app.models import Organization
from app.models.enums import DocumentStatus, DocumentType
from app.schemas.document import (
    DocumentDetailRead,
    DocumentListResponse,
    EventLogRead,
    DocumentFieldsUpdate,
    DocumentDecisionRequest,
)
from app.services.document_query_service import (
    DocumentNotFoundError,
    DocumentQueryService,
)
from app.services.document_review_service import (
    DocumentNotFoundForReviewError,
    DocumentReviewService,
    DocumentApprovalBlockedError,
    DocumentInvalidStateForReviewError,
)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


@router.get(
    "",
    response_model=DocumentListResponse,
)
def list_documents(
    document_status: DocumentStatus | None = Query(default=None, alias="status"),
    document_type: DocumentType | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Lista documentos de la organizacion autenticada.

    Permite filtrar por status y document_type.
    """
    service = DocumentQueryService(db)

    return service.list_documents(
        current_organization=current_organization,
        status=document_status,
        document_type=document_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailRead,
)
def get_document_detail(
    document_id: uuid.UUID,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Devuelve el detalle completo de un documento.

    Si el documento existe pero pertenece a otra organizacion, respondemos 404.
    """
    service = DocumentQueryService(db)

    try:
        return service.get_document_detail(
            current_organization=current_organization,
            document_id=document_id,
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{document_id}/events",
    response_model=list[EventLogRead],
)
def list_document_events(
    document_id: uuid.UUID,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Lista el event log de un documento.
    """
    service = DocumentQueryService(db)

    try:
        return service.list_document_events(
            current_organization=current_organization,
            document_id=document_id,
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    
@router.patch(
    "/{document_id}/fields",
)
def update_document_fields(
    document_id: uuid.UUID,
    payload: DocumentFieldsUpdate,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Corrige campos extraidos y vuelve a validar el documento.
    """
    service = DocumentReviewService(db)

    try:
        return service.update_fields(
            current_organization=current_organization,
            document_id=document_id,
            data=payload,
        )

    except DocumentNotFoundForReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    
@router.post(
    "/{document_id}/approve",
)
def approve_document(
    document_id: uuid.UUID,
    payload: DocumentDecisionRequest,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Aprueba un documento que esta en revision humana.
    """
    service = DocumentReviewService(db)

    try:
        return service.approve_document(
            current_organization=current_organization,
            document_id=document_id,
            reviewer_id=payload.reviewer_id,
        )

    except DocumentNotFoundForReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DocumentInvalidStateForReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DocumentApprovalBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/{document_id}/reject",
)
def reject_document(
    document_id: uuid.UUID,
    payload: DocumentDecisionRequest,
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Rechaza un documento que esta en revision humana.
    """
    service = DocumentReviewService(db)

    try:
        return service.reject_document(
            current_organization=current_organization,
            document_id=document_id,
            reviewer_id=payload.reviewer_id,
            reason=payload.reason,
        )

    except DocumentNotFoundForReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DocumentInvalidStateForReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc