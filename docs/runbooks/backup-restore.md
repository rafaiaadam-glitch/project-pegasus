# Backup and restore runbook (Postgres + object storage)

This runbook defines the minimum operational procedure for backing up and restoring Pegasus data.

## Scope

- Postgres data (`courses`, `lectures`, `jobs`, `artifacts`, `threads`, `exports`)
- Object storage paths referenced by the DB (`audio`, `transcripts`, `exports`, artifact files)

## Backup policy (minimum)

- **Postgres**
  - Daily full snapshot
  - Point-in-time recovery (PITR) enabled where available
  - Retention: 7 days minimum for MVP, 30 days recommended
- **Object storage**
  - Daily bucket sync or provider snapshot
  - Versioning enabled where possible
  - Retention aligned with Postgres backup retention

## Pre-restore checklist

1. Confirm incident scope (DB corruption, accidental deletion, storage loss).
2. Freeze writes by scaling API worker traffic down or enabling maintenance mode.
3. Record incident start timestamp and target restore timestamp.
4. Notify stakeholders that a restore is in progress.

---

## GCP Cloud SQL backup (production)

### Create on-demand backup

```bash
gcloud sql backups create \
  --instance=pegasus-db-eu \
  --project=delta-student-486911-n5 \
  --description="Manual backup $(date +%F-%H%M)"
```

### List available backups

```bash
gcloud sql backups list \
  --instance=pegasus-db-eu \
  --project=delta-student-486911-n5
```

### Restore from backup (in-place)

```bash
# Find the backup ID from the list command above
BACKUP_ID=<backup-id>

gcloud sql backups restore "$BACKUP_ID" \
  --restore-instance=pegasus-db-eu \
  --project=delta-student-486911-n5
```

### Restore via PITR (point-in-time recovery)

Clone the instance to a specific point in time. This creates a new instance — useful for testing the restore before switching over.

```bash
RESTORE_TIMESTAMP="2025-06-15T14:30:00.000Z"  # RFC 3339

gcloud sql instances clone pegasus-db-eu pegasus-db-eu-restored \
  --point-in-time="$RESTORE_TIMESTAMP" \
  --project=delta-student-486911-n5
```

After validation, update the `pegasus-db-url` secret in Secret Manager to point to the restored instance, then restart Cloud Run:

```bash
gcloud run services update pegasus-api \
  --region=europe-west1 \
  --project=delta-student-486911-n5 \
  --update-env-vars=FORCE_RESTART=$(date +%s)
```

---

## GCS object storage backup (production)

### Verify object versioning is enabled

```bash
gcloud storage buckets describe gs://delta-student-486911-n5-pegasus-storage-eu \
  --format="value(versioning_enabled)"
```

### Enable object versioning (if not already)

```bash
gcloud storage buckets update gs://delta-student-486911-n5-pegasus-storage-eu \
  --versioning
```

### Copy objects to a backup bucket

```bash
BACKUP_DATE=$(date +%F)
gcloud storage cp --recursive \
  gs://delta-student-486911-n5-pegasus-storage-eu/pegasus/ \
  gs://delta-student-486911-n5-pegasus-backup-eu/pegasus-$BACKUP_DATE/
```

### Restore a deleted or overwritten object from a version

```bash
# List versions of a specific object
gcloud storage ls -l --all-versions \
  "gs://delta-student-486911-n5-pegasus-storage-eu/pegasus/path/to/object"

# Restore a specific version by copying it back
gcloud storage cp \
  "gs://delta-student-486911-n5-pegasus-storage-eu/pegasus/path/to/object#<generation>" \
  "gs://delta-student-486911-n5-pegasus-storage-eu/pegasus/path/to/object"
```

### Restore from backup bucket

```bash
gcloud storage cp --recursive \
  gs://delta-student-486911-n5-pegasus-backup-eu/pegasus-YYYY-MM-DD/ \
  gs://delta-student-486911-n5-pegasus-storage-eu/pegasus/
```

---

## Fallback: logical backup (self-managed / local Postgres)

### Logical backup

```bash
pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL" > pegasus_$(date +%F).dump
```

### Restore logical backup

```bash
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname "$DATABASE_URL" pegasus_YYYY-MM-DD.dump
```

---

## Restore workflow

1. Restore Postgres to target timestamp/snapshot (Cloud SQL backup or PITR clone).
2. Restore object storage snapshot to matching point in time (GCS versioning or backup bucket).
3. Start API/worker in read-only or low-traffic mode.
4. Run integrity checks:

```bash
API_BASE_URL="https://pegasus-api-988514135894.europe-west1.run.app"
curl -sS "$API_BASE_URL/health/ready"
curl -sS "$API_BASE_URL/lectures/<lecture-id>/integrity"
```

5. Validate queue behavior with a smoke job (`scripts/smoke_worker_queue.sh`).
6. Re-enable traffic.

## Verification checklist

- `GET /health/ready` returns `ready`.
- Sample lecture transcript is retrievable.
- Artifact and export paths exist for sampled lectures.
- New ingest + generate + export flow succeeds.

## Failure handling

- If restore validation fails, roll forward to a newer backup snapshot.
- If DB and storage snapshots are mismatched, repeat restore using matched timestamps.
- Document incident timeline, root cause, and data-loss window.

## Drill script

Run `ops/drills/backup-restore-drill.sh` to execute a non-destructive backup/restore cycle and capture evidence logs. See `ops/drills/` for details.
