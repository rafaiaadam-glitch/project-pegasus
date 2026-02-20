# Deployment Guide — Cloud Run (Production)

Canonical deployment guide for the Pegasus API on Google Cloud Run (europe-west1).

For multi-platform reference (Render, Fly.io, Railway, local Docker), see `docs/deploy.md`.

---

## Prerequisites

- `gcloud` CLI authenticated with project `delta-student-486911-n5`
- Docker (used by Cloud Build)
- Access to Secret Manager secrets: `pegasus-db-url`, `openai-api-key`
- Cloud SQL instance `pegasus-db-eu` running in europe-west1

## Architecture Overview

```
Mobile app
  └─► Cloud Run (pegasus-api, europe-west1)
        ├─ FastAPI backend
        ├─ Inline job runner (PLC_INLINE_JOBS=1)
        ├─► Cloud SQL PostgreSQL 14 (pegasus-db-eu, europe-west1)
        ├─► GCS bucket (delta-student-486911-n5-pegasus-storage-eu)
        └─► OpenAI API (Whisper STT + gpt-4o-mini LLM + chat)
```

- **No separate worker process** — jobs run inline in the request handler.
- **No Redis** — `PLC_INLINE_JOBS=1` bypasses the queue.
- Image builds in us-central1 Artifact Registry; Cloud Run pulls cross-region (supported).

## Build & Deploy

```bash
cd temp-repo && gcloud builds submit --config=cloudbuild.yaml --region=us-central1
```

This single command builds the Docker image, pushes to Artifact Registry, and deploys to Cloud Run with all configured health checks, scaling, and environment variables.

### What `cloudbuild.yaml` configures

| Setting | Value | Rationale |
|---|---|---|
| Memory | 2 Gi | Handles audio transcoding + LLM payloads |
| CPU | 2 | Concurrent request handling |
| Min instances | 0 | Scale to zero when idle |
| Max instances | 4 | Cost cap for MVP |
| Timeout | 300s | Long-running transcription jobs |
| Concurrency | 80 | Requests per instance |
| Startup probe | `/health`, 60s window | Allows DB migrations to complete |
| Liveness probe | `/health/live`, every 30s | Lightweight process-alive check |

## Environment Variables

Set automatically by `cloudbuild.yaml`:

| Variable | Value | Source |
|---|---|---|
| `STORAGE_MODE` | `gcs` | cloudbuild.yaml |
| `GCS_BUCKET` | `$PROJECT_ID-pegasus-storage-eu` | cloudbuild.yaml |
| `GCS_PREFIX` | `pegasus` | cloudbuild.yaml |
| `PLC_LLM_PROVIDER` | `openai` | cloudbuild.yaml |
| `GCP_PROJECT_ID` | `$PROJECT_ID` | cloudbuild.yaml |
| `GCP_REGION` | `europe-west1` | cloudbuild.yaml |
| `PLC_INLINE_JOBS` | `1` | cloudbuild.yaml |
| `DATABASE_URL` | (connection string) | Secret Manager: `pegasus-db-url` |
| `OPENAI_API_KEY` | (API key) | Secret Manager: `openai-api-key` |

### Update env vars without redeploying

```bash
gcloud run services update pegasus-api \
  --region=europe-west1 \
  --project=delta-student-486911-n5 \
  --update-env-vars=KEY=VALUE
```

## Health Checks

| Endpoint | Purpose | Checks |
|---|---|---|
| `GET /health` | Startup probe | Returns `{"status": "ok"}` — confirms process started |
| `GET /health/ready` | Readiness (manual) | Database, queue, storage checks; returns 503 if degraded |
| `GET /health/live` | Liveness probe | Returns `{"status": "ok"}` — no dependency checks |

### Verify after deploy

```bash
# Service URL
SERVICE_URL=https://pegasus-api-988514135894.europe-west1.run.app

# Liveness
curl -sS "$SERVICE_URL/health/live"
# → {"status": "ok"}

# Startup / basic health
curl -sS "$SERVICE_URL/health"
# → {"status": "ok", "time": "..."}

# Readiness (full dependency check)
curl -sS "$SERVICE_URL/health/ready"
# → {"status": "ok", "time": "...", "checks": {...}}
```

## Scaling

| Parameter | Value | Notes |
|---|---|---|
| Min instances | 0 | Saves cost; cold start ~5-10s with startup CPU boost |
| Max instances | 4 | MVP ceiling — increase for production load |
| Concurrency | 80 | Per-instance concurrent requests |
| Startup CPU boost | Enabled | Extra CPU during cold start for faster init |

To adjust scaling:

```bash
gcloud run services update pegasus-api \
  --region=europe-west1 \
  --project=delta-student-486911-n5 \
  --min-instances=1 --max-instances=8
```

## Viewing Logs

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=pegasus-api AND resource.labels.location=europe-west1 AND severity>=INFO" \
  --limit 20 --project=delta-student-486911-n5
```

## Troubleshooting

### Cold start timeout
- Startup probe allows 60s (6 attempts x 10s period). If migrations are slow, increase `--startup-probe-failure-threshold`.
- `--startup-cpu-boost` is enabled to speed up init.

### 503 from readiness check
- Check which component is degraded in the `/health/ready` response.
- Database: verify Cloud SQL instance is running and `DATABASE_URL` secret is correct (no trailing newline).
- Storage: verify GCS bucket exists and service account has `storage.objects.create` permission.

### Deploy fails
- Verify `gcloud auth list` shows correct account.
- Verify Artifact Registry repo exists: `gcloud artifacts repositories list --location=us-central1`.
- Check build logs: `gcloud builds list --region=us-central1 --limit=5`.

### Secret issues
- `DATABASE_URL` must not have a trailing newline. Update with:
  ```bash
  printf 'postgresql://...' | gcloud secrets versions add pegasus-db-url --data-file=-
  ```

## Related Documentation

- Multi-platform deployment: `docs/deploy.md`
- Release checklist: `docs/release-checklist.md`
- Staging parity: `docs/staging-parity-checklist.md`
- Incident response: `docs/runbooks/incident-response.md`
- Backup/restore: `docs/runbooks/backup-restore.md`
- Secrets management: `docs/runbooks/secrets-management.md`
