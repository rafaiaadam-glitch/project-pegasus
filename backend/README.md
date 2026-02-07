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

## Environment

- `OPENAI_API_KEY` (required for LLM-backed generation)
- `OPENAI_MODEL` (optional, default: `gpt-4o-mini`)
- `PLC_STORAGE_DIR` (optional, default: `storage`)
- `DATABASE_URL` (required, Postgres/Supabase)
- `STORAGE_MODE` (`local` or `s3`)
- `S3_BUCKET` / `S3_PREFIX` (required when `STORAGE_MODE=s3`)

## Endpoints

- `GET /health`
- `POST /lectures/ingest` (multipart upload)
- `POST /lectures/{lecture_id}/transcribe`
- `POST /lectures/{lecture_id}/generate`
- `POST /lectures/{lecture_id}/export`
- `GET /jobs/{job_id}`
