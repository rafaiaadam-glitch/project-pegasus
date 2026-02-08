# Pegasus API (FastAPI)

Minimal backend aligned with the MVP stack (FastAPI + local storage).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Run

```bash
uvicorn backend.app:app --reload --port 8000
```

## Worker

```bash
python -m backend.worker
```

Job status is persisted in Postgres (see `DATABASE_URL`) and processed via Redis/RQ
with retry/backoff defaults.

Migrations are applied from `backend/migrations` on startup.

Ensure the API and worker services use the same `DATABASE_URL`, `REDIS_URL`,
OpenAI, and storage-related environment variables so jobs can be enqueued and
processed consistently.

## Environment

- `OPENAI_API_KEY` (required for LLM-backed generation)
- `OPENAI_MODEL` (optional, default: `gpt-4o-mini`)
- `PLC_STORAGE_DIR` (optional, default: `storage`)
- `DATABASE_URL` (required, Postgres/Supabase)
- `REDIS_URL` (optional, default: `redis://localhost:6379/0`)
- `STORAGE_MODE` (`local` or `s3`)
- `S3_BUCKET` / `S3_PREFIX` (required when `STORAGE_MODE=s3`)

## Endpoints

- `GET /health`
- `POST /lectures/ingest` (multipart upload)
- `POST /lectures/{lecture_id}/transcribe`
- `POST /lectures/{lecture_id}/generate` (JSON body: `{"course_id":"...","preset_id":"...","openai_model":"..."}`; `openai_model` optional)
- `POST /lectures/{lecture_id}/export`
- `GET /exports/{lecture_id}/{export_type}`
- `GET /lectures/{lecture_id}/artifacts` (query params: `artifact_type`, `preset_id`, `limit`, `offset`; includes `artifactDownloadUrls` for S3-backed artifacts)
- `GET /lectures/{lecture_id}/summary`
- `GET /jobs/{job_id}`
