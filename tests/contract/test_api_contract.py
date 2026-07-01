import time
import uuid
from pathlib import Path

import requests


API_BASE_URL = "http://localhost:8000/api/v1"
ROOT_URL = "http://localhost:8000"


def assert_success(response: requests.Response) -> None:
    """
    Valida que una respuesta HTTP sea exitosa.

    Si falla, muestra status code y body para que sea fácil
    encontrar el problema desde la terminal.
    """
    assert response.ok, (
        f"Expected success but got {response.status_code}: {response.text}"
    )


def create_test_organization() -> dict:
    """
    Crea una organización única para esta corrida de tests.

    Usamos uuid en el slug para evitar choques con datos anteriores
    que ya existan en la base local.
    """
    unique_id = uuid.uuid4().hex[:8]

    payload = {
        "name": f"Contract Test Org {unique_id}",
        "slug": f"contract-test-org-{unique_id}",
        "status": "active",
    }

    response = requests.post(
        f"{API_BASE_URL}/organizations",
        json=payload,
        timeout=10,
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_api_key(organization_id: str) -> str:
    """
    Genera una API key real para la organización de prueba.

    La API key solo se devuelve una vez, así que el test la conserva
    en memoria para el resto de requests.
    """
    response = requests.post(
        f"{API_BASE_URL}/organizations/{organization_id}/api-keys",
        timeout=10,
    )

    assert response.status_code == 201, response.text

    body = response.json()
    assert body["api_key"].startswith("byp_")

    return body["api_key"]


def auth_headers(api_key: str) -> dict[str, str]:
    """
    Construye headers autenticados para endpoints protegidos.
    """
    return {
        "X-API-Key": api_key,
    }

def create_test_batch(api_key: str, name: str = "Pytest batch") -> dict:
    response = requests.post(
        f"{API_BASE_URL}/batches",
        json={
            "name": name,
            "source": "pytest",
            "metadata": {"created_by": "pytest"},
        },
        headers=auth_headers(api_key),
        timeout=10,
    )

    assert response.status_code == 201, response.text
    return response.json()


def upload_text_document(
    *,
    api_key: str,
    batch_id: str,
    tmp_path: Path,
    filename: str,
    content: str,
    idempotency_key: str | None = None,
    mime_type: str = "text/plain",
    source_reference: str = "pytest-upload",
) -> requests.Response:
    test_file = tmp_path / filename
    test_file.write_text(content, encoding="utf-8")

    headers = auth_headers(api_key)

    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    with test_file.open("rb") as file_handler:
        return requests.post(
            f"{API_BASE_URL}/batches/{batch_id}/documents",
            headers=headers,
            files={
                "file": (
                    filename,
                    file_handler,
                    mime_type,
                ),
            },
            data={
                "source_reference": source_reference,
            },
            timeout=20,
        )

def upsert_validation_rule(
    *,
    api_key: str,
    organization_id: str,
    document_type: str,
    required_fields: list[str],
) -> dict:
    response = requests.put(
        f"{API_BASE_URL}/organizations/{organization_id}/validation-rules",
        headers=auth_headers(api_key),
        json={
            "document_type": document_type,
            "required_fields": required_fields,
        },
        timeout=10,
    )

    assert response.ok, response.text
    return response.json()

def test_health_endpoint_is_available() -> None:
    """
    Verifica que la API esté viva antes de probar flujos de negocio.
    """
    response = requests.get(f"{ROOT_URL}/health", timeout=10)

    assert_success(response)


def test_full_intake_contract_flow(tmp_path: Path) -> None:
    """
    Prueba el contrato principal del sistema de punta a punta.

    Flujo cubierto:
    - crear organización
    - generar API key
    - autenticar organización
    - crear batch
    - subir documento
    - consultar progreso
    - consultar documentos
    - consultar métricas
    """
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    headers = auth_headers(api_key)

    me_response = requests.get(
        f"{API_BASE_URL}/organizations/me",
        headers=headers,
        timeout=10,
    )

    assert_success(me_response)
    assert me_response.json()["id"] == organization["id"]

    batch_payload = {
        "name": "Contract test batch",
        "source": "contract_test",
        "metadata": {
            "created_by": "pytest",
        },
    }

    batch_response = requests.post(
        f"{API_BASE_URL}/batches",
        json=batch_payload,
        headers=headers,
        timeout=10,
    )

    assert batch_response.status_code == 201, batch_response.text

    batch = batch_response.json()
    assert batch["organization_id"] == organization["id"]
    assert batch["name"] == "Contract test batch"

    test_file = tmp_path / "contract_invoice.txt"
    test_file.write_text(
        "Factura contract test total 1234 MXN",
        encoding="utf-8",
    )

    with test_file.open("rb") as file_handler:
        upload_response = requests.post(
            f"{API_BASE_URL}/batches/{batch['id']}/documents",
            headers={
                **headers,
                "Idempotency-Key": f"contract-upload-{uuid.uuid4()}",
            },
            files={
                "file": (
                    "contract_invoice.txt",
                    file_handler,
                    "text/plain",
                ),
            },
            data={
                "source_reference": "contract-test-upload",
            },
            timeout=20,
        )

    assert upload_response.status_code == 201, upload_response.text

    document = upload_response.json()
    assert document["batch_id"] == batch["id"]
    assert document["filename"] == "contract_invoice.txt"
    assert document["status"] in {
        "uploaded",
        "queued",
        "extracting",
        "classified",
        "needs_review",
        "approved",
    }

    final_document = wait_for_document_to_finish(
        api_key=api_key,
        document_id=document["id"],
    )

    assert final_document["status"] in {
        "needs_review",
        "approved",
        "rejected",
        "failed",
    }

    progress_response = requests.get(
        f"{API_BASE_URL}/batches/{batch['id']}/progress",
        headers=headers,
        timeout=10,
    )

    assert_success(progress_response)

    progress = progress_response.json()
    assert progress["batch_id"] == batch["id"]
    assert progress["total_documents"] >= 1
    assert "progress_percent" in progress

    documents_response = requests.get(
        f"{API_BASE_URL}/documents",
        headers=headers,
        timeout=10,
    )

    assert_success(documents_response)
    assert documents_response.json()["total"] >= 1

    metrics_response = requests.get(
        f"{API_BASE_URL}/metrics",
        headers=headers,
        timeout=10,
    )

    assert_success(metrics_response)

    metrics = metrics_response.json()
    assert metrics["documents_total"] >= 1
    assert metrics["batches_total"] >= 1


def wait_for_document_to_finish(
    *,
    api_key: str,
    document_id: str,
    attempts: int = 15,
    sleep_seconds: float = 1.0,
) -> dict:
    """
    Espera a que el worker procese el documento.

    El endpoint de upload responde rápido con status queued.
    El worker procesa después, por eso hacemos polling controlado.
    """
    terminal_statuses = {
        "approved",
        "needs_review",
        "rejected",
        "failed",
    }

    headers = auth_headers(api_key)

    for _ in range(attempts):
        response = requests.get(
            f"{API_BASE_URL}/documents/{document_id}",
            headers=headers,
            timeout=10,
        )

        assert_success(response)

        document = response.json()

        if document["status"] in terminal_statuses:
            return document

        time.sleep(sleep_seconds)

    raise AssertionError(
        f"Document {document_id} did not finish processing in time"
    )

def test_same_idempotency_key_returns_same_upload_snapshot(tmp_path: Path) -> None:
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    batch = create_test_batch(api_key)

    idem_key = f"same-upload-{uuid.uuid4()}"

    first_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="same_idem.txt",
        content="Factura total 100 MXN",
        idempotency_key=idem_key,
    )

    second_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="same_idem.txt",
        content="Factura total 100 MXN",
        idempotency_key=idem_key,
    )

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 201, second_response.text

    assert second_response.json()["id"] == first_response.json()["id"]
    assert second_response.json()["checksum_sha256"] == first_response.json()["checksum_sha256"]


def test_same_document_with_different_idempotency_key_is_duplicate(tmp_path: Path) -> None:
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    batch = create_test_batch(api_key)

    first_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="duplicate.txt",
        content="Factura total 200 MXN",
        idempotency_key=f"first-{uuid.uuid4()}",
    )

    second_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="duplicate.txt",
        content="Factura total 200 MXN",
        idempotency_key=f"second-{uuid.uuid4()}",
    )

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 201, second_response.text

    first_document = first_response.json()
    second_document = second_response.json()

    assert second_document["id"] != first_document["id"]
    assert second_document["is_duplicate_candidate"] is True
    assert second_document["duplicate_of_document_id"] == first_document["id"]


def test_same_idempotency_key_with_different_request_returns_conflict(tmp_path: Path) -> None:
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    batch = create_test_batch(api_key)

    idem_key = f"conflict-{uuid.uuid4()}"

    first_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="idem_conflict_a.txt",
        content="Factura total 300 MXN",
        idempotency_key=idem_key,
    )

    second_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="idem_conflict_b.txt",
        content="Factura total 999 MXN",
        idempotency_key=idem_key,
    )

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 409
    assert "Idempotency-Key" in second_response.text


def test_document_from_other_organization_cannot_be_read(tmp_path: Path) -> None:
    org_a = create_test_organization()
    api_key_a = create_api_key(org_a["id"])
    batch_a = create_test_batch(api_key_a)

    org_b = create_test_organization()
    api_key_b = create_api_key(org_b["id"])

    upload_response = upload_text_document(
        api_key=api_key_a,
        batch_id=batch_a["id"],
        tmp_path=tmp_path,
        filename="private_doc.txt",
        content="Factura total 400 MXN",
        idempotency_key=f"private-{uuid.uuid4()}",
    )

    assert upload_response.status_code == 201, upload_response.text

    document_id = upload_response.json()["id"]

    cross_tenant_response = requests.get(
        f"{API_BASE_URL}/documents/{document_id}",
        headers=auth_headers(api_key_b),
        timeout=10,
    )

    assert cross_tenant_response.status_code == 404


def test_retry_document_that_is_not_failed_returns_conflict(tmp_path: Path) -> None:
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    batch = create_test_batch(api_key)

    upload_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="retry_not_failed.txt",
        content="Factura total 500 MXN",
        idempotency_key=f"retry-{uuid.uuid4()}",
    )

    assert upload_response.status_code == 201, upload_response.text

    retry_response = requests.post(
        f"{API_BASE_URL}/documents/{upload_response.json()['id']}/retry",
        headers=auth_headers(api_key),
        json={"reviewer_id": "pytest-reviewer"},
        timeout=10,
    )

    assert retry_response.status_code == 409


def test_approve_document_with_missing_required_fields_is_blocked(tmp_path: Path) -> None:
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    batch = create_test_batch(api_key)

    upsert_validation_rule(
        api_key=api_key,
        organization_id=organization["id"],
        document_type="invoice",
        required_fields=["vendor", "total", "currency", "document_date", "tax_id"],
    )

    upload_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="missing_tax_id.txt",
        content="Factura total 600 MXN",
        idempotency_key=f"missing-{uuid.uuid4()}",
    )

    assert upload_response.status_code == 201, upload_response.text

    document = wait_for_document_to_finish(
        api_key=api_key,
        document_id=upload_response.json()["id"],
    )

    approve_response = requests.post(
        f"{API_BASE_URL}/documents/{document['id']}/approve",
        headers=auth_headers(api_key),
        json={"reviewer_id": "pytest-reviewer"},
        timeout=10,
    )

    assert approve_response.status_code == 422


def test_correct_fields_and_approve_document(tmp_path: Path) -> None:
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    batch = create_test_batch(api_key)

    upsert_validation_rule(
        api_key=api_key,
        organization_id=organization["id"],
        document_type="invoice",
        required_fields=["vendor", "total", "currency", "document_date", "tax_id"],
    )

    upload_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="correct_tax_id.txt",
        content="Factura total 700 MXN",
        idempotency_key=f"correct-{uuid.uuid4()}",
    )

    assert upload_response.status_code == 201, upload_response.text

    document = wait_for_document_to_finish(
        api_key=api_key,
        document_id=upload_response.json()["id"],
    )

    update_response = requests.patch(
        f"{API_BASE_URL}/documents/{document['id']}/fields",
        headers=auth_headers(api_key),
        json={
            "reviewer_id": "pytest-reviewer",
            "fields": {
                "tax_id": "RFC-PYTEST-123",
            },
        },
        timeout=10,
    )

    assert update_response.ok, update_response.text
    assert update_response.json()["missing_fields"] == []

    approve_response = requests.post(
        f"{API_BASE_URL}/documents/{document['id']}/approve",
        headers=auth_headers(api_key),
        json={"reviewer_id": "pytest-reviewer"},
        timeout=10,
    )

    assert approve_response.ok, approve_response.text
    assert approve_response.json()["status"] == "approved"


def test_upload_with_invalid_mime_type_is_rejected(tmp_path: Path) -> None:
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    batch = create_test_batch(api_key)

    response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="bad_file.exe",
        content="not really an exe",
        idempotency_key=f"bad-mime-{uuid.uuid4()}",
        mime_type="application/x-msdownload",
    )

    assert response.status_code == 415

def test_retry_document_stuck_in_extracting_requeues_document(tmp_path: Path) -> None:
    organization = create_test_organization()
    api_key = create_api_key(organization["id"])
    batch = create_test_batch(api_key)

    upload_response = upload_text_document(
        api_key=api_key,
        batch_id=batch["id"],
        tmp_path=tmp_path,
        filename="stuck_extracting.txt",
        content="Factura total 800 MXN",
        idempotency_key=f"stuck-{uuid.uuid4()}",
    )

    assert upload_response.status_code == 201, upload_response.text

    document_id = upload_response.json()["id"]

    import psycopg

    with psycopg.connect(
        "postgresql://byepaper:byepaper@localhost:5432/byepaper"
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE documents SET status = 'EXTRACTING' WHERE id = %s",
                (document_id,),
            )

    retry_response = requests.post(
        f"{API_BASE_URL}/documents/{document_id}/retry",
        headers=auth_headers(api_key),
        json={"reviewer_id": "pytest-reviewer"},
        timeout=10,
    )

    assert retry_response.ok, retry_response.text
    assert retry_response.json()["status"] == "queued"

    recovered_document = wait_for_document_to_finish(
        api_key=api_key,
        document_id=document_id,
        attempts=20,
        sleep_seconds=1,
    )

    assert recovered_document["status"] in {
        "approved",
        "needs_review",
    }