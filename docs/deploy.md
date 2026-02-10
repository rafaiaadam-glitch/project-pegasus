# Deployment Notes (MVP)

This repo ships with local scripts, a FastAPI backend, and a React Native client.
To deploy the MVP, you will need:

- Postgres (Supabase recommended)
- S3-compatible storage (or Supabase Storage)
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
- `STORAGE_MODE` (`local` or `s3`)
- `S3_BUCKET`, `S3_PREFIX` (if `STORAGE_MODE=s3`)
- `S3_ENDPOINT_URL` (optional, for S3-compatible storage)
- `S3_REGION` / `AWS_REGION` (optional, for S3-compatible storage)
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

Automated option:

```bash
API_BASE_URL=https://your-api.example.com ./scripts/smoke_worker_queue.sh
```

This script executes health, ingest, enqueue, and job polling steps and exits non-zero on failure/timeout. By default, terminal `failed` still counts as queue/worker-path success (override with `SMOKE_ACCEPT_FAILED_TERMINAL=0`).

Queue/worker validation behavior:
- `SMOKE_REQUIRE_QUEUE_PATH=1` (default) enforces that jobs do **not** use inline fallback (`queueFallback=inline` fails the run).
- `SMOKE_REQUIRE_RUNNING_STATE=1` (optional) requires observing `running` during polling before terminal completion. This can be flaky for very fast jobs; leave it `0` unless you need strict transition checks.
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

## Mobile

Use EAS Build (Expo) for iOS/Android distribution.

1. Install the EAS CLI: `npm install -g eas-cli`
2. Authenticate: `eas login`
3. Configure builds: `eas build:configure`
4. Run builds:
   - iOS: `eas build --platform ios`
   - Android: `eas build --platform android`

Set `API_BASE_URL` in `mobile/App.tsx` to the deployed backend URL.
