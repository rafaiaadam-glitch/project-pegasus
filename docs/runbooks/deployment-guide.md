# Canonical Deployment Guide (API + Worker + Storage)

This is the canonical production deployment guide for Pegasus.

## Scope

This guide covers the minimum production topology:
- API service (`uvicorn backend.app:app`)
- Worker service (`python -m backend.worker`)
- Shared durable storage (`s3` or `gcs`)
- Shared Postgres + Redis between API and worker

## Prerequisites

- Provisioned Postgres and Redis
- Provisioned storage bucket/container
- Runtime secrets configured for both API and worker
- Migrations available under `backend/migrations/`

## Required environment variables (API + Worker)

The API and worker **must** share identical values for:
- `DATABASE_URL`
- `REDIS_URL`
- `STORAGE_MODE`
- `S3_BUCKET`/`S3_PREFIX` (for S3)
- `GCS_BUCKET`/`GCS_PREFIX` (for GCS)
- `PLC_LLM_PROVIDER` + model/provider credentials

Runtime validation references:
- `backend/runtime_config.py`
- `backend/tests/test_runtime_config.py`

## Platform deployment mappings

### Render
- Config: `render.yaml`
- API readiness: `healthCheckPath: /health/ready`
- Worker start command: `python -m backend.worker`

### Railway
- API config: `railway.toml`
- Worker config: `railway.worker.toml`
- API readiness: `healthcheckPath = "/health/ready"`

### Fly.io
- Config: `fly.toml`
- API + worker process groups in one app
- API readiness check via `[[http_service.checks]]` path `/health/ready`

## Deployment procedure

1. Set env vars and secrets for API + worker.
2. Deploy API and verify:
   - `GET /health` returns `ok`
   - `GET /health/ready` returns `ready`
3. Deploy worker and verify startup logs show queue polling.
4. Run migration-safe smoke flow:
   - ingest lecture
   - enqueue transcription/generation/export
   - verify artifacts and export URLs

## Post-deploy verification

- API readiness endpoint healthy over 5+ minutes
- Worker processes jobs from shared queue
- DB writes visible across API and worker paths
- Storage read/write validated for output artifacts

## Rollback reference

For migration rollback and incident rollback decisions, follow:
- `docs/runbooks/migration-rollback.md`
- `docs/runbooks/incident-response.md`
