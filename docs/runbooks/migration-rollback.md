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

## Rollback options

### Option A (preferred): restore database to pre-migration snapshot

1. Identify pre-deploy restore point (timestamp or snapshot ID).
2. Restore DB using provider PITR/snapshot tooling.
3. Repoint API/worker to restored DB (or restore in-place).
4. Restore storage snapshot only if migration included destructive data-path updates.

### Option B: apply corrective forward migration

Use when restore is too disruptive and issue can be fixed safely.

1. Create a new migration file with lexicographically higher version (e.g. `002_fix_...sql`).
2. Make changes idempotent (`IF EXISTS` / `IF NOT EXISTS`).
3. Validate against staging clone before production deploy.

## Post-rollback validation

1. Confirm service readiness:

```bash
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
