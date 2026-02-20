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
LLM/transcription provider, and storage-related environment variables so jobs can be enqueued and
processed consistently.

## Environment


Startup validates runtime configuration with clear errors: `DATABASE_URL` is always required; `REDIS_URL` is required unless `PLC_INLINE_JOBS` is enabled for API (worker always requires Redis); and storage env is validated based on `STORAGE_MODE`.

- `PLC_LLM_PROVIDER` (optional, default: `openai`; supports `openai`, `gemini`, `vertex`)
- `OPENAI_API_KEY` (required — used for transcription, LLM generation, and chat)
- `OPENAI_MODEL` (optional default model for OpenAI path, default: `gpt-4o-mini`)
- `PLC_CHAT_MODEL` (optional, default: `gpt-4o-mini` — model used for chat endpoint)
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` (optional, legacy — only needed when `PLC_LLM_PROVIDER=gemini|vertex`)
- `PLC_GCP_STT_MODEL` (optional, default: `latest_long` for `provider=google` transcription — legacy)
- `PLC_STT_LANGUAGE` (optional, default: `en-US` for `provider=google` transcription — legacy)
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
- `PLC_RETENTION_RAW_AUDIO_DAYS` (optional, default: `30`; raw audio retention period in days for cleanup)
- `PLC_RETENTION_TRANSCRIPT_DAYS` (optional, default: `14`; transcript retention period in days for cleanup)
- `STORAGE_MODE` (`local`, `s3`, or `gcs`)
- `S3_BUCKET` / `S3_PREFIX` (required when `STORAGE_MODE=s3`, and `S3_PREFIX` must be non-empty)
- `S3_ENDPOINT_URL` (optional, for S3-compatible storage)
- `S3_REGION` / `AWS_REGION` (optional, for S3-compatible storage)
- `GCS_BUCKET` / `GCS_PREFIX` (required when `STORAGE_MODE=gcs`, and `GCS_PREFIX` must be non-empty)
- `GOOGLE_APPLICATION_CREDENTIALS` (required in most non-GCP runtimes for `STORAGE_MODE=gcs`)

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
- `POST /lectures/ingest` (multipart upload; accepts optional `lecture_mode` and stores it in lecture metadata as `lectureMode`)
- `GET /lectures` (supports `course_id`, `status`, `preset_id`, `limit`, and `offset`; includes `pagination`)
- `GET /lectures/{lecture_id}`
- `GET /lectures/{lecture_id}/transcript` (returns transcript text + segments; supports `include_text` and `segment_limit`)
- `POST /lectures/{lecture_id}/transcribe` (supports `provider=openai|whisper|google`, default `openai`; optional `language_code`; deduplicates when a transcription job for the lecture is already `queued`/`running`)
- `POST /lectures/{lecture_id}/generate` (JSON body: `{"course_id":"...","preset_id":"...","llm_provider":"openai|gemini","llm_model":"..."}`; `course_id` and `preset_id` optional and default from ingested lecture; if provided they must match ingested lecture; deduplicates when a generation job for the lecture is already `queued`/`running`)
- `POST /lectures/{lecture_id}/export` (deduplicates when an export job for the lecture is already `queued`/`running`)
- `DELETE /lectures/{lecture_id}` (deletes lecture row plus related jobs/artifacts/exports; optional `purge_storage=true|false`)
- `DELETE /courses/{course_id}` (deletes course and cascades lecture deletions; optional `purge_storage=true|false`)

When `PLC_WRITE_API_TOKEN` is configured, every `POST /lectures/*` endpoint requires a matching bearer token. Missing/invalid auth returns `401`; wrong token returns `403`.
Write endpoints are also rate-limited per client (`x-forwarded-for` first, then socket IP) and return `429` with `Too many write requests. Please retry shortly.` when limits are exceeded.
Write endpoints also support optional `Idempotency-Key` headers: repeated requests with the same key and payload replay the original response, while reuse with a different payload returns `409`.
- `GET /lectures/{lecture_id}/jobs` (supports `limit` and `offset`; includes `pagination`)
- `GET /lectures/{lecture_id}/progress` (includes `overallStatus`, per-stage status, `progressPercent`, `currentStage`, `hasFailedStage`, and lecture endpoint links)
- `GET /exports/{lecture_id}/{export_type}`
- `GET /lectures/{lecture_id}/artifacts` (query params: `artifact_type`, `preset_id`, `limit`, `offset`; includes `artifactDownloadUrls` and `pagination` (`nextOffset`/`prevOffset` included))
- `GET /lectures/{lecture_id}/summary` (compact lecture dashboard: artifact/export counts + stage progress snapshot + lecture/export links)
- `GET /lectures/{lecture_id}/integrity` (verifies DB-referenced storage paths for audio/transcript/artifacts/exports and reports missing files)
- `GET /jobs/{job_id}`
- `GET /jobs/dead-letter` (lists failed jobs; supports `lecture_id`, `job_type`, `limit`, `offset`)
- `POST /jobs/{job_id}/replay` (requeues only `failed` jobs for transcription/generation/export; returns 409 for non-failed jobs)
- `POST /jobs/dead-letter/replay` (batch replay failed jobs; supports `lecture_id`, `job_type`, `limit`)


Operational runbook: `docs/runbooks/dead-letter-queue.md`.


Retention cleanup job:

```bash
python -m backend.retention
```

Use `--dry-run` to preview candidate deletions without removing storage paths.

### Web E2E checks (Playwright)

- Local run: `npm run test:e2e`
- CI/container run (installs Chromium + required system libraries): `npm run test:e2e:ci`
- If your environment blocks apt/system package installs, pre-bake Playwright dependencies into the build image before running `test:e2e`.


### GCP live-test wiring

Use this when you want to run the backend/worker against GCP Cloud Storage:

1. Set storage env vars for **both** API and worker:
   - `STORAGE_MODE=gcs`
   - `GCS_BUCKET=<your-bucket>`
   - `GCS_PREFIX=pegasus`
2. Ensure ADC/service-account auth is available:
   - local: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`
   - GCP runtime: attach a service account with Storage Object Admin (or narrower write/read perms).
3. Sanity-check wiring before live testing:
   - `python -c "from backend.runtime_config import validate_runtime_environment; validate_runtime_environment('api')"`
   - then run ingest and verify returned `audioPath`/artifact paths use `gs://...`.
- Run: `npm run test:e2e`
- Note: CI/container environments may need system browser libraries (for example `libatk-1.0.so.0`) for Chromium to launch.
