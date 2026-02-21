# Migration rollback runbook

Use this runbook when a schema migration causes production errors.

## Constraints

- Migrations in `backend/migrations` are applied automatically at startup.
- There is no in-app `down` migration executor; rollback is operational via restore + patch migration.

## Trigger conditions

- API/worker fails after deploy with migration-related errors.
- New queries fail due to schema mismatch.
- Elevated 5xx rates start immediately after release.

## Immediate response

1. Stop rollout (pause deploy pipeline, scale down new release).
2. Keep one healthy version active if possible.
3. Capture failing migration filename from logs (`backend/migrations/*.sql`).

---

## Rollback options

### Option A (preferred): restore database to pre-migration snapshot

#### GCP Cloud SQL — PITR restore

Clone the database to a point in time before the bad migration was applied:

```bash
# Use a timestamp from BEFORE the deploy that applied the migration
PRE_MIGRATION_TIMESTAMP="2025-06-15T14:00:00.000Z"  # RFC 3339

gcloud sql instances clone pegasus-db-eu pegasus-db-eu-rollback \
  --point-in-time="$PRE_MIGRATION_TIMESTAMP" \
  --project=delta-student-486911-n5
```

Then update the `pegasus-db-url` secret to point at the new instance:

```bash
# Get the new instance IP
gcloud sql instances describe pegasus-db-eu-rollback \
  --project=delta-student-486911-n5 \
  --format="value(ipAddresses[0].ipAddress)"

# Update the secret (replace NEW_CONNECTION_STRING with actual value)
echo -n "$NEW_CONNECTION_STRING" | \
  gcloud secrets versions add pegasus-db-url \
  --data-file=- \
  --project=delta-student-486911-n5
```

#### GCP Cloud SQL — snapshot restore (in-place)

If PITR is not available, restore the most recent pre-deploy backup:

```bash
# List backups
gcloud sql backups list \
  --instance=pegasus-db-eu \
  --project=delta-student-486911-n5

# Restore (pick the backup ID from BEFORE the deploy)
BACKUP_ID=<pre-deploy-backup-id>
gcloud sql backups restore "$BACKUP_ID" \
  --restore-instance=pegasus-db-eu \
  --project=delta-student-486911-n5
```

#### Cloud Run — revert to previous revision

Roll back the API to the pre-deploy revision so the old code (without the bad migration) is running:

```bash
# List recent revisions
gcloud run revisions list \
  --service=pegasus-api \
  --region=europe-west1 \
  --project=delta-student-486911-n5 \
  --limit=5

# Route 100% traffic to the previous good revision
PREVIOUS_REVISION="pegasus-api-XXXXX"  # from the list above
gcloud run services update-traffic pegasus-api \
  --region=europe-west1 \
  --project=delta-student-486911-n5 \
  --to-revisions="$PREVIOUS_REVISION=100"
```

4. Restore storage snapshot only if migration included destructive data-path updates.

### Option B: apply corrective forward migration

Use when restore is too disruptive and issue can be fixed safely.

1. Create a new migration file with lexicographically higher version (e.g. `002_fix_...sql`).
2. Make changes idempotent (`IF EXISTS` / `IF NOT EXISTS`).
3. Validate against staging clone before production deploy.

---

## Post-rollback validation

1. Confirm service readiness:

```bash
API_BASE_URL="https://pegasus-api-988514135894.europe-west1.run.app"
curl -sS "$API_BASE_URL/health/ready"
```

2. Validate core read/write paths:

```bash
curl -sS "$API_BASE_URL/courses"
curl -sS "$API_BASE_URL/lectures"
```

3. Validate job flow using queue smoke test:

```bash
API_BASE_URL="$API_BASE_URL" ./scripts/smoke_worker_queue.sh
```

## Preventive controls for future migrations

- Always run migrations against staging first with production-like data volume.
- Prefer additive migrations before destructive cleanup.
- For destructive changes, split into 2 releases:
  - Release 1: additive schema + dual-write/read compatibility.
  - Release 2: cleanup after verification.
- Require migration checklist in PR:
  - rollback strategy,
  - expected lock behavior,
  - data backfill plan,
  - runtime compatibility notes.
