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
- `PLC_INLINE_JOBS` (optional, `true/1/on` runs jobs inline in API process; useful for local MVP without Redis)
- `STORAGE_MODE` (`local` or `s3`)
- `S3_BUCKET` / `S3_PREFIX` (required when `STORAGE_MODE=s3`)
- `S3_ENDPOINT_URL` (optional, for S3-compatible storage)
- `S3_REGION` / `AWS_REGION` (optional, for S3-compatible storage)

## Endpoints

- `GET /health`
- `GET /health/ready` (readiness probe for database, queue, and storage)
- `GET /presets`
- `GET /presets/{preset_id}`
- `GET /courses`
- `GET /courses/{course_id}`
- `GET /courses/{course_id}/lectures` (404 if course does not exist)
- `GET /courses/{course_id}/threads`
- `GET /courses/{course_id}/progress` (404 if course does not exist; supports `include_lectures=false`; includes `overallStatus`, status-count rollups, `latestActivityAt`, and optional per-lecture stage snapshots with endpoint links)
- `POST /lectures/ingest` (multipart upload)
- `GET /lectures`
- `GET /lectures/{lecture_id}`
- `POST /lectures/{lecture_id}/transcribe`
- `POST /lectures/{lecture_id}/generate` (JSON body: `{"course_id":"...","preset_id":"...","openai_model":"..."}`; `course_id` and `preset_id` optional and default from ingested lecture; if provided they must match ingested lecture)
- `POST /lectures/{lecture_id}/export`
- `GET /lectures/{lecture_id}/jobs`
- `GET /lectures/{lecture_id}/progress` (includes `overallStatus`, per-stage status, `progressPercent`, `currentStage`, `hasFailedStage`, and lecture endpoint links)
- `GET /exports/{lecture_id}/{export_type}`
- `GET /lectures/{lecture_id}/artifacts` (query params: `artifact_type`, `preset_id`, `limit`, `offset`; includes `artifactDownloadUrls` for S3-backed artifacts)
- `GET /lectures/{lecture_id}/summary` (compact lecture dashboard: artifact/export counts + stage progress snapshot + lecture/export links)
- `GET /jobs/{job_id}`
