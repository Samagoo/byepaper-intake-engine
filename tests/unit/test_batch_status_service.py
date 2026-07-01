from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.models.enums import BatchStatus, DocumentStatus
from app.services.batch_status_service import BatchStatusService


def test_batch_with_failed_and_approved_documents_is_partially_failed() -> None:
    service = BatchStatusService.__new__(BatchStatusService)

    status = service._derive_status(
        [
            DocumentStatus.APPROVED,
            DocumentStatus.FAILED,
        ]
    )

    assert status == BatchStatus.PARTIALLY_FAILED


def test_batch_with_only_approved_or_rejected_documents_is_completed() -> None:
    service = BatchStatusService.__new__(BatchStatusService)

    status = service._derive_status(
        [
            DocumentStatus.APPROVED,
            DocumentStatus.REJECTED,
        ]
    )

    assert status == BatchStatus.COMPLETED


def test_empty_batch_is_created() -> None:
    service = BatchStatusService.__new__(BatchStatusService)

    status = service._derive_status([])

    assert status == BatchStatus.CREATED