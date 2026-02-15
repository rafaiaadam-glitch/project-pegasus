# Release Checklist with Rollback Procedure

Use this checklist for each production release.

## Pre-release

- [ ] Main branch is green (tests + security scans).
- [ ] Staging parity checklist completed: `docs/runbooks/staging-parity-checklist.md`.
- [ ] Backup/restore readiness verified: `docs/runbooks/backup-restore.md`.
- [ ] Rollback plan reviewed: `docs/runbooks/migration-rollback.md`.
- [ ] Required on-call contacts are available for release window.

## Deploy steps

1. Deploy API revision.
2. Validate API readiness endpoint (`/health/ready`).
3. Deploy worker revision.
4. Confirm worker startup/migration logs are healthy.
5. Run queue smoke test (`scripts/smoke_worker_queue.sh`).

## Post-deploy validation

- [ ] `GET /health` returns ok.
- [ ] `GET /health/ready` returns ready.
- [ ] One synthetic ingest→transcribe→generate→export flow succeeds (or fails with expected controlled error).
- [ ] No sustained failure spikes in metrics.
- [ ] No dead-letter backlog growth after deploy.

## Rollback triggers

Rollback should start immediately when any of the following is true:
- readiness remains unhealthy beyond grace period,
- error-rate spike is sustained above acceptable threshold,
- queue backlog grows without recovery after mitigation,
- data corruption risk is detected.

## Rollback procedure (high level)

1. Freeze new deploys.
2. Route traffic to previous stable API revision.
3. Roll back worker to previous stable revision.
4. If schema or data issue exists, follow `docs/runbooks/migration-rollback.md`.
5. If data integrity issue exists, restore from backup per `docs/runbooks/backup-restore.md`.
6. Re-run smoke tests to confirm stabilization.

## Release record template

- Release ID / commit SHA:
- Release owner:
- Start time (UTC):
- End time (UTC):
- Outcome: success / rolled back
- Smoke-test evidence links:
- Incident/ticket links:
