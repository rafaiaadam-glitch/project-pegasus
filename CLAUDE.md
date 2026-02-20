# Pegasus Project - CLAUDE.md

## Project Overview
Lecture companion app: upload audio/PDF → STT transcription → Thread Engine (concept extraction + artifact generation via single LLM call) → Export.

## Tech Stack
- **Backend:** FastAPI (Python 3.11), deployed on Cloud Run (europe-west1)
- **Mobile:** React Native / Expo SDK 54 (TypeScript)
- **Database:** Cloud SQL PostgreSQL 14 (`pegasus-db-eu`, europe-west1)
- **Storage:** GCS bucket `delta-student-486911-n5-pegasus-storage-eu`
- **LLM:** OpenAI API (`gpt-4o-mini` default) — Thread Engine makes a single call that generates both threads and artifacts
- **STT:** OpenAI Whisper API (`whisper-1`) — handles any audio format, 25MB limit with auto-compression
- **Chat:** OpenAI API (`gpt-4o-mini` default via `PLC_CHAT_MODEL`)
- **GCP Project:** `delta-student-486911-n5`
- **Service Account:** `pegasus-api@delta-student-486911-n5.iam.gserviceaccount.com`

## Architecture: Pipeline Flow
```
Upload audio/PDF (via signed URL → GCS direct)
  → OpenAI Whisper transcription (whisper-1, auto-compress >25MB)
  → Thread Engine (single OpenAI API call via /v1/responses):
      - Extracts concepts/threads
      - Generates all artifacts (summary, outline, key-terms, flashcards, exam-questions)
  → Schema validation + save to GCS
  → Export (markdown, PDF, Anki CSV)
```

**There is NO separate generation step.** `pipeline/llm_generation.py` is legacy — the Thread Engine handles everything in one LLM call via OpenAI. The `run_pipeline.py` gets artifacts from `thread_engine.get_last_artifacts()`.

## Upload Flow (Mobile → Backend)
1. Mobile calls `POST /upload/signed-url` with filename + content_type
2. Backend returns a GCS signed URL (using service account access token)
3. Mobile uploads file directly to GCS via PUT to signed URL
4. Mobile calls `POST /lectures/ingest` with `storage_path` (GCS reference)
5. Backend creates lecture record, enqueues `run_transcription_job` (Google STT)
6. Jobs run inline (`PLC_INLINE_JOBS=1`) — transcription happens synchronously

## Repository Structure
- Git repo root: `temp-repo/` (not the project root)
- `temp-repo/backend/` — FastAPI backend
- `temp-repo/pipeline/` — Thread Engine, pipeline runner, export
- `temp-repo/mobile/` — React Native app
- `temp-repo/cloudbuild.yaml` — Build & deploy config

**IMPORTANT:** There is also a root `project-pegasus/backend/` and `project-pegasus/mobile/` which are more up-to-date copies. The `temp-repo/` versions are what gets deployed. When syncing, copy root files to temp-repo but preserve temp-repo's `jobs.py` (has STT V1 changes) and `cloudbuild.yaml` (has europe-west1 config).

## Key Files
- `backend/app.py` — API routes, `/upload/signed-url`, `/lectures/ingest`, all CRUD endpoints
- `backend/jobs.py` — Job runners: `run_transcription_job` (STT V1), `run_generation_job`, `run_export_job`
- `backend/storage.py` — Storage abstraction (local/GCS/S3), includes `generate_upload_signed_url()`
- `backend/chat.py` — Chat endpoint (Gemini-powered)
- `backend/db.py` — Database layer (psycopg v3), migrations, all queries
- `pipeline/thread_engine.py` — Core LLM component: concept extraction + artifact generation via `_call_vertex_sdk()`
- `pipeline/run_pipeline.py` — Orchestrates: Thread Engine → wraps artifacts in envelopes → validates → saves
- `pipeline/llm_generation.py` — LEGACY, no longer used in pipeline
- `mobile/src/services/api.ts` — API client (signed URL upload, ingest, CRUD, chat)
- `mobile/src/screens/RecordLectureScreen.tsx` — Upload screen (signed URL flow with progress)
- `mobile/.env` — `EXPO_PUBLIC_API_URL` pointing to Cloud Run europe-west1

## Deployment (europe-west1) — DEPLOYED AND LIVE

| Resource | Value |
|---|---|
| Service URL | `pegasus-api-988514135894.europe-west1.run.app` |
| Cloud SQL | `pegasus-db-eu` (europe-west1) |
| Cloud SQL Instance | `delta-student-486911-n5:europe-west1:pegasus-db-eu` |
| GCS Bucket | `delta-student-486911-n5-pegasus-storage-eu` |
| `GCP_REGION` | `europe-west1` |
| `PLC_LLM_REGION` | `us-central1` (Vertex AI models aren't in europe-west1) |
| DB User | `pegasus_user` (password in Secret Manager `pegasus-db-url`) |

### Deploy Command
```bash
# Build in us-central1 Artifact Registry, deploy to europe-west1 Cloud Run
cd temp-repo && gcloud builds submit --config=cloudbuild.yaml --region=us-central1
```

### View Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=pegasus-api AND resource.labels.location=europe-west1 AND severity>=INFO" --limit 20 --project=delta-student-486911-n5
```

### Update Env Vars Without Redeploying
```bash
gcloud run services update pegasus-api --region=europe-west1 --project=delta-student-486911-n5 --update-env-vars=KEY=VALUE
```

## What Still Needs Doing

### Step 1: Test End-to-End
1. Upload a file via mobile app (signed URL → GCS → ingest)
2. Verify STT transcription completes (check logs for `long_running_recognize`)
3. Tap Generate → verify Thread Engine uses Vertex AI SDK (look for `[ThreadEngine] Calling Vertex AI SDK` in logs)
4. Verify artifacts are generated and visible in the app

### Step 2: Set LLM Model Env Var (optional)
The Thread Engine reads `PLC_LLM_MODEL` for the model name. Default is `gemini-2.0-flash`. To change:
```bash
gcloud run services update pegasus-api --region=europe-west1 --project=delta-student-486911-n5 \
  --update-env-vars=PLC_LLM_MODEL=gemini-2.0-flash
```

## Code Changes Made & Deployed

### 1. Thread Engine: Vertex AI SDK + Artifact Generation
`pipeline/thread_engine.py`:
- Added `_call_vertex_sdk()` — uses Vertex AI SDK with service account credentials
- Updated `_build_system_prompt()` — accepts `generate_artifacts=True`
- Updated `generate_thread_records()` — detects `GCP_PROJECT_ID` → uses Vertex AI SDK
- Added `_last_artifacts` + `get_last_artifacts()` for pipeline to retrieve artifacts
- Provider order: OpenAI (if key) → Gemini REST (if key) → Vertex AI SDK (if GCP_PROJECT_ID) → fallback

### 2. Pipeline: Thread Engine Does Everything
`pipeline/run_pipeline.py`:
- `_generate_thread_records()` passes `generate_artifacts=True` when `use_llm=True`
- Added `_wrap_thread_engine_artifacts()` — wraps raw LLM output in schema-conformant envelopes

### 3. STT: Google Speech-to-Text V1 Long Audio
`backend/jobs.py`:
- `_transcribe_with_google_speech()` accepts `gcs_uri` parameter
- GCS: converts to FLAC (mono 16kHz) → uploads to GCS temp → `long_running_recognize` → cleanup
- Local: >1MB → `long_running_recognize`, small → synchronous `recognize`

### 4. Ingest: Uses STT (not Gemini fast-ingest)
`backend/app.py`:
- `/lectures/ingest` enqueues `run_transcription_job` (Google STT) instead of `run_fast_ingest_job`
- Upload via signed URL: `POST /upload/signed-url` → GCS direct PUT → ingest with `storage_path` reference

### 5. Backend: Synced from root project
- `app.py`, `storage.py`, `db.py`, `presets.py`, `chat.py`, `observability.py` — all synced from root `project-pegasus/backend/`
- `jobs.py` kept from temp-repo (has STT V1 changes, root has V2 batch which is different)
- `db.py` uses psycopg v3 (not psycopg2)

### 6. Mobile: Synced from root project
- All screens, components, theme files synced from root `project-pegasus/mobile/`
- `api.ts` from root (has `getUploadUrl`, `uploadToSignedUrl`, `ingestLecture`)
- `.env` updated to `https://pegasus-api-988514135894.europe-west1.run.app`

### 7. Database
- `pegasus-db-url` secret updated to europe-west1 socket path
- `pegasus_user` password set on `pegasus-db-eu` instance

## Artifact Schema Reference
Schemas live in `schemas/artifacts/`. Key fields for each artifact (envelope fields like id, courseId, etc. are added by `_wrap_thread_engine_artifacts`):

| Artifact | Schema Key Fields |
|---|---|
| summary | `overview` (string), `sections` (array of `{title, bullets}`) |
| outline | `outline` (array of `{title, points?, children?}`) |
| key-terms | `terms` (array of `{term, definition}`) |
| flashcards | `cards` (array of `{front, back, difficulty?, tags?}`) |
| exam-questions | `questions` (array of `{prompt, type, answer, choices?, correctChoiceIndex?}`) |

## Git Workflow
- Repo root is `temp-repo/`, always use `git -C temp-repo/`
- Mobile app is at `temp-repo/mobile/`
- Expo dev server: run from `temp-repo/mobile/` (NOT root `mobile/`)
- Current branch: `main`

## Gotchas
- **Two copies of code exist:** root `project-pegasus/` has newer mobile/backend code; `temp-repo/` is what deploys. Sync root → temp-repo but preserve temp-repo's `jobs.py` and `cloudbuild.yaml`
- **Expo must run from `temp-repo/mobile/`** — root `mobile/` has old api.ts without correct backend URL
- `DATABASE_URL` secret must NOT have a trailing newline
- `cloudbuild.yaml` builds from `temp-repo/` context with `backend/Dockerfile`
- `cloudbuild.yaml` `--set-cloudsql-instances` overrides any manual `gcloud run services update` on each deploy — make sure it's correct in the yaml
- `PLC_INLINE_JOBS=1` runs jobs synchronously in the request handler (no Redis worker)
- Vertex AI SDK does NOT accept `location="global"` — use a real region like `us-central1`
- Thread Engine has 3 LLM paths: OpenAI REST (needs key), Gemini REST (needs key), Vertex AI SDK (uses service account — primary path on Cloud Run)
- `pipeline/llm_generation.py` is LEGACY — not called by the pipeline anymore
- Artifact schemas use `additionalProperties: false` — the LLM output must not have extra fields or validation fails
- Image builds in us-central1 Artifact Registry but Cloud Run pulls cross-region to europe-west1 (fine)
- `PLC_LLM_REGION=us-central1` is separate from `GCP_REGION=europe-west1` — LLM models aren't available in europe-west1
- `db.py` uses psycopg v3 (root), but `jobs.py` may reference psycopg2 patterns — they're independent
- Root `jobs.py` uses STT V2 batch; temp-repo `jobs.py` uses STT V1 `long_running_recognize` — don't overwrite
