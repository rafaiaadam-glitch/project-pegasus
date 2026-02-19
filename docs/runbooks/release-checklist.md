# Release Checklist with Rollback Procedure

Use this checklist for every production release.

## Pre-release checks

- [ ] Main branch green in CI
- [ ] No HIGH/CRITICAL vulnerabilities in current build scan
- [ ] Migration impact reviewed (forward + rollback plan)
- [ ] API + worker env var diffs reviewed against last release

## Deploy sequence

1. Deploy API
2. Verify `GET /health/ready`
3. Deploy worker
4. Run smoke flow: ingest → transcribe → generate → export
5. Monitor queue depth/failure-rate/latency for 15 minutes

## Success criteria

- API/worker remain healthy
- No sustained failure spike alerts
- No queue backlog growth trend
- Export artifacts available for smoke test lecture

## Rollback procedure

Trigger rollback if any of these occur:
- sustained API readiness failures
- sustained worker failure spike or dead-letter growth
- data integrity regressions in generated artifacts/exports

### Step-by-step rollback

1. Freeze new writes if incident severity requires it.
2. Roll back API and worker images to previous known-good build.
3. If migration-related, execute rollback from:
   - `docs/runbooks/migration-rollback.md`
4. Validate:
   - `GET /health/ready`
   - worker queue resumes normal processing
   - smoke flow passes on canary lecture
5. Record incident timeline and commands in runbook notes.

## Required release artifacts

- Deployed commit SHA
- Smoke test lecture/job IDs
- Rollback decision log (if invoked)
- Links to alert and dashboard snapshots
