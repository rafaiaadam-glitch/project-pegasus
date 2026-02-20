# Pegasus Project - CLAUDE.md

## Project Overview
Lecture companion app: upload audio/PDF → OpenAI Whisper transcription → Thread Engine (concept extraction + artifact generation via single OpenAI API call) → Export.

## Tech Stack
- **Backend:** FastAPI (Python 3.11), deployed on Cloud Run (europe-west1)
- **Mobile:** React Native / Expo SDK 54 (TypeScript)
- **Database:** Cloud SQL PostgreSQL 14 (`pegasus-db-eu`, europe-west1)
- **Storage:** GCS bucket `delta-student-486911-n5-pegasus-storage-eu`
- **LLM:** OpenAI API (`gpt-4o-mini` default) — Thread Engine makes a single call that generates both threads and artifacts
- **STT:** OpenAI Whisper API (`whisper-1`) — handles any audio format, 25MB limit with auto-compression
- **Chat:** OpenAI API (`gpt-4o-mini` default via `PLC_CHAT_MODEL`)
- **GCP Project:** `delta-student-486911-n5` (used for GCS storage + Cloud SQL only)
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
5. Backend creates lecture record, enqueues `run_transcription_job` (OpenAI Whisper)
6. Jobs run inline (`PLC_INLINE_JOBS=1`) — transcription happens synchronously

## Repository Structure
- Git repo root: `temp-repo/` (not the project root)
- `temp-repo/backend/` — FastAPI backend
- `temp-repo/pipeline/` — Thread Engine, pipeline runner, export
- `temp-repo/mobile/` — React Native app
- `temp-repo/cloudbuild.yaml` — Build & deploy config

## Key Files
- `backend/app.py` — API routes, `/upload/signed-url`, `/lectures/ingest`, all CRUD endpoints
- `backend/jobs.py` — Job runners: `run_transcription_job` (OpenAI Whisper), `run_generation_job`, `run_export_job`
- `backend/storage.py` — Storage abstraction (local/GCS/S3), includes `generate_upload_signed_url()`
- `backend/chat.py` — Chat endpoint (OpenAI-powered, `gpt-4o-mini`)
- `backend/db.py` — Database layer (psycopg v3), migrations, all queries
- `pipeline/thread_engine.py` — Core LLM component: concept extraction + artifact generation via `_call_openai()`
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
| DB User | `pegasus_user` (password in Secret Manager `pegasus-db-url`) |

### Cloud Run Environment
- `PLC_LLM_PROVIDER=openai`
- `OPENAI_API_KEY` from Secret Manager (`openai-api-key`)
- `DATABASE_URL` from Secret Manager (`pegasus-db-url`)
- `STORAGE_MODE=gcs`, `GCS_BUCKET`, `GCS_PREFIX=pegasus`
- `PLC_INLINE_JOBS=1`

### Deploy Command
```bash
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

## Artifact Schema Reference
Schemas live in `schemas/artifacts/`. Key fields for each artifact (envelope fields like id, courseId, etc. are added by `_wrap_thread_engine_artifacts`):

| Artifact | Schema Key Fields |
|---|---|
| summary | `overview` (string), `sections` (array of `{title, bullets}`) |
| outline | `outline` (array of `{title, points?, children?}`) |
| key-terms | `terms` (array of `{term, definition}`) |
| flashcards | `cards` (array of `{front, back, difficulty?, tags?}`) |
| exam-questions | `questions` (array of `{prompt, type, answer, choices?, correctChoiceIndex?}`) |

**Important:** Schemas use `additionalProperties: false` — LLM output is sanitized by `_strip_nulls()` in `run_pipeline.py` to remove null values and unexpected keys before validation.

## Git Workflow
- Repo root is `temp-repo/`, always use `git -C temp-repo/`
- Mobile app is at `temp-repo/mobile/`
- Expo dev server: run from `temp-repo/mobile/` (NOT root `mobile/`)
- Current branch: `main`

## Gotchas
- **Two copies of code exist:** root `project-pegasus/` has older code; `temp-repo/` is what deploys
- **Expo must run from `temp-repo/mobile/`** — root `mobile/` has old api.ts without correct backend URL
- `DATABASE_URL` secret must NOT have a trailing newline
- `cloudbuild.yaml` builds from `temp-repo/` context with `backend/Dockerfile`
- `PLC_INLINE_JOBS=1` runs jobs synchronously in the request handler (no Redis worker)
- `pipeline/llm_generation.py` is LEGACY — not called by the pipeline anymore
- Artifact schemas use `additionalProperties: false` — the LLM output must not have extra fields or validation fails
- Image builds in us-central1 Artifact Registry but Cloud Run pulls cross-region to europe-west1 (fine)
- `db.py` uses psycopg v3 — not psycopg2
- OpenAI Whisper has 25MB limit — `_transcribe_with_openai_api()` auto-compresses larger files via ffmpeg
