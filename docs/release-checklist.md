# Release Checklist

Step-by-step procedure for deploying a new release to production, with rollback instructions.

---

## Pre-Release

- [ ] All tests pass locally (`cd temp-repo && python -m pytest backend/tests/ pipeline/tests/`)
- [ ] Staging environment validated (see `docs/staging-parity-checklist.md`)
- [ ] Secrets are current (no expired keys, no pending rotations)
- [ ] No pending database migrations that require downtime
- [ ] Changes reviewed and merged to `main`

## Deploy

### 1. Submit the build

```bash
cd temp-repo && gcloud builds submit --config=cloudbuild.yaml --region=us-central1
```

### 2. Verify build succeeds

```bash
gcloud builds list --region=us-central1 --limit=1 --project=delta-student-486911-n5
```

Confirm status is `SUCCESS`. If the build fails, check logs:

```bash
gcloud builds log <BUILD_ID> --region=us-central1
```

### 3. Note the previous revision (for rollback)

```bash
gcloud run revisions list \
  --service=pegasus-api \
  --region=europe-west1 \
  --project=delta-student-486911-n5 \
  --limit=3 \
  --format='table(name, traffic_percent, creation_timestamp)'
```

Record the revision name that currently has 100% traffic.

---

## Post-Deploy Validation

### 1. Health checks

```bash
SERVICE_URL=https://pegasus-api-988514135894.europe-west1.run.app

# Liveness
curl -sS "$SERVICE_URL/health/live"
# → {"status": "ok"}

# Readiness
curl -sS "$SERVICE_URL/health/ready"
# → {"status": "ok", "time": "...", "checks": {...}}
```

### 2. Smoke test

```bash
API_BASE_URL=https://pegasus-api-988514135894.europe-west1.run.app \
  ./scripts/smoke_worker_queue.sh
```

### 3. Monitor error rate

Check logs for errors in the first 5 minutes:

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=pegasus-api AND resource.labels.location=europe-west1 AND severity>=ERROR AND timestamp>=\"$(date -u -v-5M '+%Y-%m-%dT%H:%M:%SZ')\"" \
  --limit 20 --project=delta-student-486911-n5
```

Check metrics in Cloud Run console:
- Request count and error rate
- Latency (p50, p95, p99)
- Instance count

---

## Rollback Procedure

### When to rollback

Rollback if **any** of these conditions persist for more than 5 minutes after deploy:

- Error rate > 10% of requests
- p95 latency > 30 seconds
- Health checks failing (`/health/live` or `/health/ready` returning non-200)
- Critical functionality broken (upload, transcription, or generation failing)

### How to rollback

Route 100% of traffic to the previous revision:

```bash
gcloud run services update-traffic pegasus-api \
  --region=europe-west1 \
  --project=delta-student-486911-n5 \
  --to-revisions=PREVIOUS_REVISION_NAME=100
```

Replace `PREVIOUS_REVISION_NAME` with the revision noted in the pre-deploy step.

### Verify rollback

```bash
# Confirm traffic routing
gcloud run revisions list \
  --service=pegasus-api \
  --region=europe-west1 \
  --project=delta-student-486911-n5 \
  --limit=3 \
  --format='table(name, traffic_percent)'

# Verify health
curl -sS https://pegasus-api-988514135894.europe-west1.run.app/health/live
curl -sS https://pegasus-api-988514135894.europe-west1.run.app/health/ready
```

### Post-rollback

- [ ] Verify health checks pass on rolled-back revision
- [ ] Confirm error rate has returned to normal
- [ ] File an incident report if the issue affected users (see `docs/runbooks/incident-response.md`)
- [ ] Investigate root cause before re-attempting deploy
- [ ] If the release included database migrations, check if rollback guidance is needed (see `docs/runbooks/migration-rollback.md`)

---

## Database Migration Releases

If the release includes schema changes:

1. Ensure migrations are backwards-compatible (additive only: new columns with defaults, new tables)
2. Deploy the new code — migrations auto-apply on startup via `Database.migrate()`
3. If rollback is needed and migrations were applied, consult `docs/runbooks/migration-rollback.md`

Avoid destructive migrations (dropping columns/tables) in the same release as the code change. Use a two-phase approach:
1. Release 1: Deploy code that stops using the old column
2. Release 2: Drop the old column

---

## Related Documentation

- Deployment guide: `docs/deployment-guide.md`
- Staging parity: `docs/staging-parity-checklist.md`
- Incident response: `docs/runbooks/incident-response.md`
- Backup/restore: `docs/runbooks/backup-restore.md`
- Migration rollback: `docs/runbooks/migration-rollback.md`
