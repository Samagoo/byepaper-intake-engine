# ByePaper Intake Engine

ByePaper Intake Engine is a simplified document ingestion and processing platform built for the ByePaper Senior Backend Engineer challenge.

The system allows organizations to upload documents, group them into batches, process them asynchronously, extract simulated fields, validate business rules, detect duplicates, support human review, and keep a complete event log for auditability.

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- RQ worker
- Docker Compose

### Frontend
- React
- TypeScript
- Vite

### Testing and API validation
- Pytest
- Requests
- Postman collection

---

## Main Features

- Organization creation
- API key generation with hashed storage
- Multi-tenant access isolation by `organization_id`
- Batch creation and listing
- Document upload with metadata persistence
- MIME type and size validation
- SHA-256 checksum calculation
- Duplicate detection inside the same organization
- Idempotent document upload using `Idempotency-Key`
- Asynchronous document processing with Redis + RQ worker
- Simulated extraction, classification, confidence score and validation
- Validation rules per organization and document type
- Human review flow
- Field correction and revalidation
- Approve, reject and retry actions
- Event log for important transitions
- Derived batch status from document statuses
- Operational metrics endpoint
- Rate limiting by API key
- Basic React frontend for the full review flow
- Postman collection for manual API testing
- Contract smoke tests for the main API flow

---

## Project Architecture

The project is organized in layers to avoid placing business logic directly inside FastAPI endpoints.

```text
Frontend React + TypeScript
        |
        v
FastAPI API
        |
        v
Services / Use cases
        |
        v
Repositories
        |
        v
PostgreSQL

Infrastructure:
- Redis / RQ queue
- Worker process
- Storage adapter
- API key hashing
- Request logging
- Rate limiting
```

### Main Components

| Component | Responsibility |
|---|---|
| Frontend | User interface for organization onboarding, batches, documents, progress, review actions and audit log. |
| FastAPI API | Receives HTTP requests, validates input, authenticates API keys and delegates business logic. |
| Services | Contain business rules for upload, idempotency, validation, review and retry flows. |
| Repositories | Encapsulate database reads and writes. |
| PostgreSQL | Stores organizations, API keys, batches, documents, fields, validation errors, events and idempotency records. |
| Redis | Queue backend for asynchronous document processing. |
| Worker | Processes documents outside the request/response cycle. |
| Storage | Stores uploaded files outside the database. Current implementation uses local storage behind an adapter. |

---

## Data Model Overview

Main entities:

```text
Organization
  ├── ApiKey
  ├── Batch
  │     └── Document
  │           ├── ExtractedField
  │           ├── ValidationError
  │           └── EventLog
  ├── ValidationRule
  └── IdempotencyRecord
```

Important rule:

```text
Almost every business query is scoped by organization_id.
Resources are never fetched only by id when they belong to a tenant.
```

This prevents one organization from reading or modifying another organization's resources.

---

## Document State Model

Documents move through controlled states.

```text
uploaded -> queued -> extracting -> classified -> needs_review -> approved
                                                        └────────> rejected
```

Failure flow:

```text
uploaded -> queued -> extracting -> failed -> retry_requested -> queued
```

| State | Meaning |
|---|---|
| uploaded | The file was received and metadata was created. |
| queued | A processing job was queued. |
| extracting | The worker is extracting or simulating document text. |
| classified | The document type was detected. |
| needs_review | The document needs human review because confidence is low or required fields are missing. |
| approved | The document was approved by a reviewer. |
| rejected | The document was rejected by a reviewer. |
| failed | A technical processing error occurred. |

Invalid or avoided transitions:

```text
uploaded -> approved
queued -> approved
approved -> extracting
rejected -> extracting
retry when status is not failed
```

---

## Batch State Model

Batch status is derived from the statuses of its documents.

| Batch Status | Meaning |
|---|---|
| created | Batch exists but has no documents yet. |
| receiving | Batch is receiving documents. |
| processing | At least one document is still being processed or waiting for review. |
| completed | All documents reached final human states. |
| failed | All documents failed technically. |
| partially_failed | Some documents failed while others succeeded or are still pending. |

The batch status should not be treated as a manually edited switch. It is calculated from document states.

---

## API Overview

Base URL:

```text
http://localhost:8000/api/v1
```

Health endpoints:

```text
GET /health
GET /ready
```

Main API endpoints:

| Method | Endpoint | Description |
|---|---|---|
| POST | `/organizations` | Create organization |
| POST | `/organizations/{id}/api-keys` | Generate API key |
| GET | `/organizations/me` | Get current organization from API key |
| PUT | `/organizations/{id}/validation-rules` | Configure validation rules |
| POST | `/batches` | Create batch |
| GET | `/batches` | List batches |
| GET | `/batches/{id}` | Get batch detail |
| GET | `/batches/{id}/progress` | Get batch progress |
| POST | `/batches/{id}/documents` | Upload document |
| GET | `/documents` | List documents |
| GET | `/documents/{id}` | Get document detail |
| GET | `/documents/{id}/events` | Get document event log |
| PATCH | `/documents/{id}/fields` | Correct extracted fields |
| POST | `/documents/{id}/approve` | Approve document |
| POST | `/documents/{id}/reject` | Reject document |
| POST | `/documents/{id}/retry` | Retry failed document |
| GET | `/metrics` | Operational metrics |

Interactive API documentation:

```text
http://localhost:8000/docs
```

---

## Environment Variables

The project includes a root `.env.example`.

Create your local `.env` file:

```powershell
Copy-Item .env.example .env
```

Main backend variables:

| Variable | Example | Description |
|---|---|---|
| `APP_NAME` | `ByePaper Intake Engine` | Application name |
| `ENVIRONMENT` | `development` | Runtime environment |
| `API_V1_PREFIX` | `/api/v1` | API version prefix |
| `DATABASE_URL` | `postgresql+psycopg://byepaper:byepaper@db:5432/byepaper` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `RQ_QUEUE_NAME` | `document-processing` | RQ queue name |
| `STORAGE_BACKEND` | `local` | Storage adapter type |
| `LOCAL_STORAGE_PATH` | `/data/storage` | Local storage path inside Docker |
| `MAX_UPLOAD_SIZE_MB` | `10` | Max upload size in MB |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` | Max upload size in bytes |
| `ALLOWED_MIME_TYPES` | `application/pdf,image/png,image/jpeg,text/plain` | Allowed upload MIME types |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origin |
| `LOG_LEVEL` | `INFO` | Logging level |
| `API_KEY_HASH_SECRET` | `change-this-secret-in-production` | Secret used to hash API keys |
| `RATE_LIMIT_ENABLED` | `true` | Enables API key rate limiting |
| `RATE_LIMIT_REQUESTS` | `60` | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window duration |

Frontend variable:

Create `frontend/.env.local` if needed:

```powershell
cd frontend
"VITE_API_BASE_URL=http://localhost:8000/api/v1" | Out-File -Encoding utf8 .env.local
cd ..
```

| Variable | Example | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API base URL used by React |

---

## How to Run the Project

### 1. Clone and enter the project

```powershell
git clone <repository-url>
cd byepaper-intake-engine
```

### 2. Create local environment file

```powershell
Copy-Item .env.example .env
```

### 3. Start PostgreSQL and Redis

```powershell
docker compose up -d db redis
```

### 4. Run database migrations

```powershell
docker compose run --rm api alembic upgrade head
```

### 5. Start backend API and worker

```powershell
docker compose up --build
```

This starts:

```text
byepaper-api      -> FastAPI backend on http://localhost:8000
byepaper-worker   -> RQ worker for document processing
byepaper-db       -> PostgreSQL
byepaper-redis    -> Redis
```

Backend docs:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

Readiness check:

```text
http://localhost:8000/ready
```

---

## How to Run the Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

The frontend allows the user to:

1. Create an organization.
2. Generate an API key.
3. Create batches.
4. Upload documents.
5. See batch progress.
6. Open document detail.
7. View extracted fields and validation errors.
8. Correct fields.
9. Approve, reject or retry documents.
10. View the document event log.

---

## Demo Flow from the UI

1. Open the frontend:

```text
http://localhost:5173
```

2. Click `Crear organización`.

3. Create a demo organization.

4. The frontend generates and stores an API key.

5. Create a batch.

6. Upload a `.txt`, `.pdf`, `.png` or `.jpg` document.

7. Open the batch detail screen and watch the progress update.

8. Open the document detail screen.

9. Review extracted fields, validation errors and event log.

10. Correct fields if needed.

11. Approve or reject the document.

---

## Demo Flow from Postman

The repository includes a Postman collection and local environment:

```text
postman/ByePaper.postman_collection.json
postman/ByePaper.local.postman_environment.json
```

Import both files into Postman and select the `ByePaper Local` environment.

Recommended execution order:

```text
1. Health / Health check
2. Organizations and API Keys / Create organization
3. Organizations and API Keys / Create API key
4. Organizations and API Keys / Get current organization
5. Batches / Create batch
6. Documents / Upload document
7. Batches / Get batch progress
8. Documents / Get document detail
9. Documents / Get document events
10. Metrics / Get operational metrics
```

When uploading a document, select a local file in the `file` form-data field.

If you upload another file, change the `idempotency_key` environment variable to avoid reusing the same key for a different request.

---

## Running Tests

### Backend contract tests

Make sure Docker services are running:

```powershell
docker compose up --build
```

In another terminal:

```powershell
py -m venv .venv_tests
.\.venv_tests\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
pytest tests\contract -v
```

Expected result:

```text
2 passed
```

### Frontend build check

```powershell
cd frontend
npm install
npm run build
```

### Frontend lint

```powershell
cd frontend
npm run lint
```

---

## Idempotency and Duplicate Handling

The upload endpoint supports `Idempotency-Key`.

### Same file + same Idempotency-Key

Expected behavior:

```text
Return the same response snapshot.
Do not create a second document.
```

### Same Idempotency-Key + different request

Expected behavior:

```text
Reject the request as a conflict.
The same key cannot represent two different intentions.
```

### Same file + different Idempotency-Key

Expected behavior:

```text
Create or register the new upload attempt but mark it as duplicate_candidate.
Do not silently ignore the duplicate.
```

### Duplicate scope

Duplicates are detected by checksum inside the same organization.

```text
organization_id + checksum_sha256
```

The same file uploaded by another organization should not leak information or be blocked globally.

---

## Multi-Tenant Security

Protected endpoints require:

```text
X-API-Key: <api-key>
```

API keys are not stored in plain text. The system stores a secure hash and a visible prefix.

Each API key resolves to one organization. Business queries are scoped by `organization_id`.

Example rule:

```text
Good: find document by id + organization_id
Bad:  find document only by id
```

If organization B tries to access a document from organization A, the API returns an error without exposing sensitive information.

---

## Auditing and Event Log

The system stores an event log for important transitions.

Examples:

```text
document_uploaded
document_queued
extraction_started
extraction_finished
classification_finished
validation_failed
review_updated
approved
rejected
retry_requested
```

Each event includes:

```text
timestamp
organization_id
entity_type
entity_id
event_type
actor_type
actor_id
payload
```

This allows the system to reconstruct what happened to a document instead of only storing the final status.

---

## Operational Metrics

The API exposes:

```text
GET /api/v1/metrics
```

This endpoint returns operational metrics such as total documents, failed documents, reviewed documents and batch information.

The frontend dashboard consumes this endpoint to show a high-level operational view.

---

## Architecture Decisions and Trade-offs

### FastAPI

FastAPI was selected because it provides strong request validation, automatic OpenAPI documentation and a clean structure for HTTP APIs.

### PostgreSQL

PostgreSQL is used as the source of truth for structured data, relationships, statuses, validation errors and event logs.

### Redis + RQ worker

Document processing is executed outside the API request lifecycle using Redis and RQ. This keeps upload requests fast and makes processing easier to scale.

Trade-off:

```text
RQ is simpler than Celery and appropriate for this challenge.
For a larger production system, Celery, Dramatiq or a managed queue could provide stronger retry and routing capabilities.
```

### Local storage adapter

Files are stored locally through a storage abstraction.

Trade-off:

```text
Local storage is simple for development and Docker Compose.
The abstraction allows replacing it with S3 or another object storage service later.
```

### Simulated extraction

The system simulates text extraction and classification. TXT files can be read directly, while PDF/images can use simulated output.

Trade-off:

```text
The goal of the challenge is architecture, state handling, idempotency, auditability and review flow.
Real OCR/LLM integration is intentionally left replaceable.
```

### API key authentication

The system uses API keys because the challenge focuses on organization-level ingestion rather than user login.

Trade-off:

```text
API keys are good for service-to-service ingestion.
For production human users, the system should add user authentication, roles and permissions.
```

### Polling for batch progress

The frontend uses polling to refresh batch progress.

Trade-off:

```text
Polling is simple and reliable for this challenge.
WebSockets or server-sent events would be better for high-volume real-time updates.
```

### Idempotency

The upload flow stores idempotency records to avoid duplicate documents when clients retry the same request.

Trade-off:

```text
This implementation handles repeated requests with the same key.
For production, idempotency records should have retention policies and stronger concurrency handling under high load.
```

### Batch status derivation

Batch status is derived from document states instead of being manually updated.

Trade-off:

```text
This avoids stale batch states.
It may require additional queries or cached counters in high-volume systems.
```

### Rate limiting

The API includes API-key-based rate limiting to reduce abuse and accidental request floods.

Trade-off:

```text
The local implementation is enough for the challenge.
In production, rate limiting should use shared storage and be enforced consistently across replicas.
```

---

## What Would Be Needed for Production

The current project is intentionally scoped for a technical challenge. To take it to production, the following would be needed:

1. Real OCR/LLM extraction pipeline.
2. S3-compatible object storage such as AWS S3 or MinIO.
3. Virus scanning and stricter file security.
4. User authentication for reviewers.
5. Role-based access control.
6. Stronger worker retry strategy and dead-letter queue.
7. Queue monitoring and job dashboards.
8. Centralized structured logs.
9. Distributed tracing.
10. Metrics with Prometheus/Grafana or equivalent.
11. Secrets manager instead of `.env` secrets.
12. HTTPS/TLS and production CORS configuration.
13. CI/CD pipeline with lint, tests and migrations.
14. More complete integration tests.
15. Load testing for concurrent uploads.
16. Database backup and recovery strategy.
17. Retention policies for files, events and idempotency records.
18. Automatic cleanup for files saved when a database transaction fails.
19. Production deployment manifests.
20. More robust frontend error handling and authentication flow.

---

## Useful Commands

### Start all backend services

```powershell
docker compose up --build
```

### Stop services

```powershell
docker compose down
```

### Stop services and remove volumes

Warning: this deletes local database and Redis data.

```powershell
docker compose down -v
```

### Run migrations

```powershell
docker compose run --rm api alembic upgrade head
```

### Open database shell

```powershell
docker exec -it byepaper-db psql -U byepaper -d byepaper
```

### Check API routes

```powershell
curl.exe http://localhost:8000/openapi.json
```

### Run frontend

```powershell
cd frontend
npm run dev
```

### Build frontend

```powershell
cd frontend
npm run build
```

### Run contract tests

```powershell
pytest tests\contract -v
```

---

## Troubleshooting

### `Idempotency-Key was already used for a different request`

Use a new `Idempotency-Key` when uploading a different file.

### `detail: Not Found`

Check that the API route exists in OpenAPI:

```powershell
curl.exe http://localhost:8000/openapi.json
```

Also make sure Docker is running the latest code:

```powershell
docker compose down
docker compose up --build
```

### Frontend cannot reach API

Check that backend is running:

```text
http://localhost:8000/health
```

Check `frontend/.env.local`:

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Tables do not exist

Run migrations:

```powershell
docker compose run --rm api alembic upgrade head
```

### Port already in use

Stop old containers:

```powershell
docker compose down
```

Or check if another service is using ports `8000`, `5432`, `6379` or `5173`.

---

## Repository Deliverables

This repository includes:

- Backend FastAPI application
- React + TypeScript frontend
- Docker Compose setup
- PostgreSQL database
- Redis queue
- RQ worker
- Alembic migrations
- `.env.example`
- Contract tests
- Postman collection
- README with setup and architecture notes