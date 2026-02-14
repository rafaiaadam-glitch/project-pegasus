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

## Postgres backup examples

### Logical backup (self-managed Postgres)

```bash
pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL" > pegasus_$(date +%F).dump
```

### Restore logical backup

```bash
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname "$DATABASE_URL" pegasus_YYYY-MM-DD.dump
```

## Object storage backup examples

### AWS S3 / compatible sync

```bash
aws s3 sync "s3://$S3_BUCKET/$S3_PREFIX" "s3://$BACKUP_BUCKET/$S3_PREFIX-$(date +%F)"
```

### Restore from snapshot prefix

```bash
aws s3 sync "s3://$BACKUP_BUCKET/$RESTORE_PREFIX" "s3://$S3_BUCKET/$S3_PREFIX"
```

## Restore workflow

1. Restore Postgres to target timestamp/snapshot.
2. Restore object storage snapshot to matching point in time.
3. Start API/worker in read-only or low-traffic mode.
4. Run integrity checks:

```bash
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
