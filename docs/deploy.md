# Deployment Notes (MVP)

This repo ships with local scripts, a FastAPI backend, and a React Native client.
To deploy the MVP, you will need:

- Postgres (Supabase recommended)
- S3-compatible storage, Supabase Storage, or GCS
- OpenAI API key for LLM generation
- Whisper runtime (self-hosted or API)

## Backend

Suggested platforms: Render, Fly.io, Railway, or Supabase Edge Functions (if ported).

### Local docker-compose

For a local MVP stack (API + worker + Postgres + Redis):

```bash
docker compose up --build
```

This uses `backend/Dockerfile` for both the API and worker containers and mounts
storage at `/data`.

Environment variables:
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `STORAGE_MODE` (`local`, `s3`, or `gcs`)
- `S3_BUCKET`, `S3_PREFIX` (if `STORAGE_MODE=s3`)
- `S3_ENDPOINT_URL` (optional, for S3-compatible storage)
- `S3_REGION` / `AWS_REGION` (optional, for S3-compatible storage)
- `GCS_BUCKET`, `GCS_PREFIX` (if `STORAGE_MODE=gcs`)
- `GOOGLE_APPLICATION_CREDENTIALS` (if running outside GCP with `STORAGE_MODE=gcs`)
- `PLC_STORAGE_DIR` (optional)
- `REDIS_URL` (queue/worker)

Redis target: use a managed Redis service (Render Redis, Upstash Redis, or Fly
Redis) and wire its connection string into `REDIS_URL` for both the API and
worker services.

### Supabase setup

1. Create a new Supabase project and copy the Postgres connection string into
   `DATABASE_URL`.
2. Run the backend migrations (auto-applied on startup from `backend/migrations`):
   - `courses`
   - `lectures`
   - `jobs`
   - `artifacts`
   - `threads`
   - `exports`
3. Create a storage bucket (e.g. `pegasus-assets`) and set:
   - `STORAGE_MODE=s3`
   - `S3_BUCKET=<bucket name>`
   - `S3_PREFIX=pegasus`
4. Ensure your service role or storage key is available to the backend
   environment so uploads can write to the bucket.


### GCP (Cloud Run + Cloud Storage) quick wiring

1. Run `scripts/setup-gcp.sh` to bootstrap APIs, Cloud SQL, and a storage bucket.
2. Set runtime env vars for API and worker:
   - `STORAGE_MODE=gcs`
   - `GCS_BUCKET=<bucket>`
   - `GCS_PREFIX=pegasus`
   - `DATABASE_URL=<cloud-sql-conn-string>`
   - `REDIS_URL=<managed-redis-url>`
3. Ensure service account permissions include object read/write on the bucket.
4. Smoke test:
   - ingest one lecture and verify `audioPath` starts with `gs://`
   - run generation/export and verify artifact/export storage paths are `gs://`.

### Infra configuration

Sample configs are included for Render (`render.yaml`), Fly.io (`fly.toml`), and
Railway (`railway.toml`). Each points to `backend/Dockerfile`.

Worker services:
- Render: `render.yaml` includes a worker service (`pegasus-worker`) that runs
  `python -m backend.worker`.
- Fly.io: `fly.toml` defines a `worker` process group.
- Railway: deploy a second service using `railway.worker.toml` with
  `python -m backend.worker`.

Ensure the API and worker services share identical values for `DATABASE_URL`,
`REDIS_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and storage settings (`STORAGE_MODE`,
`S3_BUCKET`, `S3_PREFIX`, `PLC_STORAGE_DIR`). This keeps job enqueueing and
processing aligned across services.

### Managed Postgres + Redis provisioning

Use managed services for durability. Provision Postgres + Redis in your target
platform and inject the connection strings into both the API and worker
services:

- Render: create a Postgres instance and a Redis instance in the Render
  dashboard, then set `DATABASE_URL` and `REDIS_URL` in both `pegasus-api` and
  `pegasus-worker` env vars.
- Fly.io: provision a Postgres cluster with `fly postgres create` and a Redis
  instance (e.g., `fly redis create` or Upstash), then set `DATABASE_URL` and
  `REDIS_URL` secrets for the app and worker process group.
- Railway: add a Postgres plugin and a Redis plugin to the project, then wire
  the generated `DATABASE_URL`/`REDIS_URL` env vars into both services.

### Secrets & env var management

Use your provider’s secrets tooling to store sensitive values:
- `DATABASE_URL`, `REDIS_URL`
- `OPENAI_API_KEY`
- `S3_BUCKET`, `S3_PREFIX`, plus any storage credentials required by your S3
  provider (or Supabase Storage keys)

Ensure the API and worker services both receive the same `DATABASE_URL`,
`REDIS_URL`, storage, and OpenAI settings so jobs can enqueue and execute
consistently.

## Migration startup check

Database migrations are applied on startup from `backend/db.py` via
`get_database()`, which runs `Database.migrate()` before returning a connection.
Both the API (`backend.app`) and worker (`backend.worker`) call `get_database()`,
so migrations should run in each service on boot.

## Release checklist

- Confirm the API and worker services have identical `DATABASE_URL`, `REDIS_URL`,
  `OPENAI_API_KEY`, `OPENAI_MODEL`, and storage settings (`STORAGE_MODE`,
  `S3_BUCKET`, `S3_PREFIX`, `PLC_STORAGE_DIR`).
- Verify Postgres and Redis services are reachable from the API and worker
  runtimes.
- Deploy migrations on the API service by triggering a restart and confirming
  `backend/migrations` has been applied (review logs for `Database.migrate()`).
- Confirm the worker service starts with no migration errors and can read the
  same database schema.
- Smoke test the job flow: upload audio, enqueue transcription, generation, and
  export, then verify job status and export URLs.


## Full deployment smoke test (worker + queue)

Use this procedure after deploy (or with local `docker compose`) to confirm API,
worker, Postgres, and Redis are correctly wired.

Preflight requirements:
- `API_BASE_URL` must point to a running Pegasus API (deployed URL or local API).
- A worker process must be running against the same `DATABASE_URL` and `REDIS_URL`
  as the API.
- Redis and Postgres must be reachable from both API and worker runtimes.
- If running locally, ensure Docker/Compose are installed before using
  `docker compose up --build`.

Automated option:

```bash
API_BASE_URL=https://your-api.example.com ./scripts/smoke_worker_queue.sh
```

This script executes health, ingest, enqueue, and job polling steps and exits non-zero on failure/timeout. By default, terminal `failed` still counts as queue/worker-path success (override with `SMOKE_ACCEPT_FAILED_TERMINAL=0`). It validates a `queued -> non-queued` transition by default (override with `SMOKE_REQUIRE_QUEUED_TRANSITION=0` only for inline/non-queue environments), and it fails by default if the job result indicates API-side queue fallback (override with `SMOKE_ALLOW_QUEUE_FALLBACK=1` only for non-worker environments).

Script-only logic validation (no live deployment):

```bash
./scripts/test_smoke_worker_queue.sh
```

This local harness stubs HTTP responses and validates success/failure branches in `scripts/smoke_worker_queue.sh`, but it does **not** replace a real deployed worker+queue smoke run.

HTTP simulation (runs full smoke script against a local fake API):

```bash
./scripts/test_smoke_worker_queue_http.sh
```

This executes all smoke-script steps (`/health`, ingest, enqueue, polling) against a temporary local server to validate integration behavior without external dependencies.

Queue/worker validation behavior:
- `SMOKE_REQUIRE_QUEUE_PATH=1` (default) enforces that jobs do **not** use inline fallback and that status reaches `running` before terminal completion.
- Set `SMOKE_REQUIRE_QUEUE_PATH=0` only when debugging environments where queue services are intentionally disabled.

### 1) Verify API health

```bash
curl -sS "$API_BASE_URL/health"
```

Expected: `{"status":"ok",...}`.

### 2) Ingest a lecture

Create a tiny placeholder WAV file (for smoke test queue validation):

```bash
python - <<'PY'
from pathlib import Path
import wave

path = Path('smoke.wav')
with wave.open(str(path), 'w') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(16000)
    wav.writeframes(b'\x00\x00' * 16000)
print(path)
PY
```

Upload it:

```bash
curl -sS -X POST "$API_BASE_URL/lectures/ingest" \
  -F "course_id=smoke-course" \
  -F "lecture_id=smoke-lecture" \
  -F "preset_id=exam" \
  -F "title=Smoke Lecture" \
  -F "audio=@smoke.wav;type=audio/wav"
```

Expected: JSON containing `lectureId` and `audioPath`.

### 3) Enqueue a transcription job

```bash
curl -sS -X POST "$API_BASE_URL/lectures/smoke-lecture/transcribe?model=base"
```

Capture `jobId` from the response.

### 4) Poll job status

```bash
curl -sS "$API_BASE_URL/jobs/$JOB_ID"
```

Poll until `status` is `succeeded` or `failed`.

Success criteria for queue/worker wiring:
- job transitions away from `queued` (proves worker consumed the queue)
- job reaches terminal state (`succeeded` or `failed`) and returns `result` or `error`

### 5) Verify worker logs

Check worker logs for dequeue + execution:

```bash
docker compose logs worker --tail=200
```

You should see the job picked up and completed/failed with a concrete reason.

### 6) (Optional) Full artifact path smoke

If transcription succeeds in your environment (Whisper/runtime configured):

```bash
curl -sS -X POST "$API_BASE_URL/lectures/smoke-lecture/generate" \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"smoke-course","preset_id":"exam"}'

curl -sS -X POST "$API_BASE_URL/lectures/smoke-lecture/export"
```

Then verify:

```bash
curl -sS "$API_BASE_URL/lectures/smoke-lecture/artifacts"
```

and export download endpoints under `/exports/{lecture_id}/{export_type}`.



### Retention automation

Schedule retention cleanup as a recurring job (daily recommended):

```bash
python -m backend.retention
```

Preview mode (no deletion):

```bash
python -m backend.retention --dry-run
```

Retention knobs:
- `PLC_RETENTION_RAW_AUDIO_DAYS` (default `30`)
- `PLC_RETENTION_TRANSCRIPT_DAYS` (default `14`)

Apply the same env values in any scheduled runner/container that executes the cleanup command.

## Incident runbooks

Operational runbooks are kept under `docs/runbooks/`:
- Backup/restore: `docs/runbooks/backup-restore.md`
- Migration rollback: `docs/runbooks/migration-rollback.md`
- Dead-letter replay: `docs/runbooks/dead-letter-queue.md`

Use these procedures during production incidents before attempting ad-hoc fixes.

## Mobile

Use EAS Build (Expo) for iOS/Android distribution.

1. Install the EAS CLI: `npm install -g eas-cli`
2. Authenticate: `eas login`
3. Configure builds: `eas build:configure`
4. Run builds:
   - iOS: `eas build --platform ios`
   - Android: `eas build --platform android`

Set `API_BASE_URL` in `mobile/App.tsx` to the deployed backend URL.
