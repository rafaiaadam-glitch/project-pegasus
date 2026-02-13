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
with retry/backoff defaults. API requests emit `x-request-id`, and worker/API job updates include structured job event logs (`job_id`, `lecture_id`, `job_type`, `status`) for traceability.

Migrations are applied from `backend/migrations` on startup.

Ensure the API and worker services use the same `DATABASE_URL`, `REDIS_URL`,
OpenAI, and storage-related environment variables so jobs can be enqueued and
processed consistently.

## Environment


Startup validates runtime configuration with clear errors: `DATABASE_URL` is always required; `REDIS_URL` is required unless `PLC_INLINE_JOBS` is enabled for API (worker always requires Redis); and storage env is validated based on `STORAGE_MODE`.

- `OPENAI_API_KEY` (required for LLM-backed generation)
- `OPENAI_MODEL` (optional, default: `gpt-4o-mini`)
- `PLC_STORAGE_DIR` (optional, default: `storage`)
- `DATABASE_URL` (required, Postgres/Supabase)
- `REDIS_URL` (optional, default: `redis://localhost:6379/0`)
- `PLC_INLINE_JOBS` (optional, `true/1/on` runs jobs inline in API process; useful for local MVP without Redis)
- `PLC_MAX_AUDIO_UPLOAD_MB` (optional, default: `200`; upload size limit enforced by `POST /lectures/ingest`)
- `PLC_WRITE_API_TOKEN` (optional; when set, all `POST /lectures/*` endpoints require `Authorization: Bearer <token>`)
- `PLC_WRITE_RATE_LIMIT_MAX_REQUESTS` (optional, default: `60`; max write requests per client within the rate-limit window)
- `PLC_WRITE_RATE_LIMIT_WINDOW_SEC` (optional, default: `60`; sliding-window duration for write rate limiting)
- `PLC_IDEMPOTENCY_TTL_SEC` (optional, default: `3600`; retention window for `Idempotency-Key` response replay)
- `PLC_EXPORT_MIN_SUMMARY_SECTIONS` (optional, default: `1`; export jobs fail when summary quality is below this threshold)
- `PLC_RETENTION_AUDIO_DAYS` (optional, default: `30`; cleanup threshold for files under `storage/audio`)
- `PLC_RETENTION_TRANSCRIPT_DAYS` (optional, default: `60`; cleanup threshold for files under `storage/transcripts`)
- `PLC_RETENTION_ARTIFACT_DAYS` (optional, default: `90`; cleanup threshold for files under `storage/artifacts`)
- `STORAGE_MODE` (`local` or `s3`)
- `S3_BUCKET` / `S3_PREFIX` (required when `STORAGE_MODE=s3`, and `S3_PREFIX` must be non-empty)
- `S3_ENDPOINT_URL` (optional, for S3-compatible storage)
- `S3_REGION` / `AWS_REGION` (optional, for S3-compatible storage)

## Endpoints

- `GET /health`
- `GET /health/ready` (readiness probe for database, queue, and storage)
- `GET /presets`
- `GET /presets/{preset_id}`
- `GET /courses` (supports `limit` and `offset`; listing responses include a `pagination` object with `count`, `total`, `hasMore`, `nextOffset`, and `prevOffset`)
- `GET /courses/{course_id}`
- `GET /courses/{course_id}/lectures` (404 if course does not exist; supports `status`, `preset_id`, `limit`, and `offset`; includes `pagination`)
- `GET /courses/{course_id}/threads` (404 if course does not exist; supports `limit` and `offset`; includes `pagination`)
- `GET /courses/{course_id}/progress` (404 if course does not exist; supports `include_lectures=false`; includes `overallStatus`, status-count rollups, `latestActivityAt`, and optional per-lecture stage snapshots with endpoint links)
- `POST /lectures/ingest` (multipart upload)
- `GET /lectures` (supports `course_id`, `status`, `preset_id`, `limit`, and `offset`; includes `pagination`)
- `GET /lectures/{lecture_id}`
- `GET /lectures/{lecture_id}/transcript` (returns transcript text + segments; supports `include_text` and `segment_limit`)
- `POST /lectures/{lecture_id}/transcribe` (deduplicates when a transcription job for the lecture is already `queued`/`running`)
- `POST /lectures/{lecture_id}/generate` (JSON body: `{"course_id":"...","preset_id":"...","openai_model":"..."}`; `course_id` and `preset_id` optional and default from ingested lecture; if provided they must match ingested lecture; deduplicates when a generation job for the lecture is already `queued`/`running`)
- `POST /lectures/{lecture_id}/export` (deduplicates when an export job for the lecture is already `queued`/`running`)
- `DELETE /lectures/{lecture_id}` (deletes lecture row plus related jobs/artifacts/exports; optional `purge_storage=true|false`)
- `DELETE /courses/{course_id}` (deletes course and cascades lecture deletions; optional `purge_storage=true|false`)

When `PLC_WRITE_API_TOKEN` is configured, every `POST /lectures/*` endpoint requires a matching bearer token. Missing/invalid auth returns `401`; wrong token returns `403`.
Write endpoints are also rate-limited per client (`x-forwarded-for` first, then socket IP) and return `429` with `Too many write requests. Please retry shortly.` when limits are exceeded.
Write endpoints also support optional `Idempotency-Key` headers: repeated requests with the same key and payload replay the original response, while reuse with a different payload returns `409`.
- `GET /lectures/{lecture_id}/jobs` (supports `status`, `limit`, and `offset`; includes `pagination`)
- `GET /jobs/failed` (returns failed jobs, optionally filtered by `lecture_id`, with pagination)
- `GET /lectures/{lecture_id}/progress` (includes `overallStatus`, per-stage status, `progressPercent`, `currentStage`, `hasFailedStage`, and lecture endpoint links)
- `GET /exports/{lecture_id}/{export_type}`
- `GET /lectures/{lecture_id}/artifacts` (query params: `artifact_type`, `preset_id`, `limit`, `offset`; includes `artifactDownloadUrls` and `pagination` (`nextOffset`/`prevOffset` included))
- `GET /lectures/{lecture_id}/summary` (compact lecture dashboard: artifact/export counts + stage progress snapshot + lecture/export links)
- `GET /lectures/{lecture_id}/integrity` (verifies DB-referenced storage paths for audio/transcript/artifacts/exports and reports missing files)
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/replay` (requeues only `failed` jobs for transcription/generation/export; returns 409 for non-failed jobs)

For dead-letter replay workflow, list failed jobs via `GET /jobs/failed`, then replay each with `POST /jobs/{job_id}/replay`.


## Retention lifecycle

Run retention cleanup (local storage mode):

```bash
python scripts/enforce_retention.py --storage-dir storage
```

You can override TTLs per run with `--audio-days`, `--transcript-days`, and `--artifact-days`.
