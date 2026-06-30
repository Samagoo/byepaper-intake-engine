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