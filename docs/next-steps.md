# Project Pegasus — What to do next

This document captures the immediate execution priorities after the current "production ready" milestone.

## Why this plan exists

There is a mismatch between:
- `docs/PRODUCTION_READINESS_STATUS.md` claiming full readiness, and
- `docs/mvp-launch-checklist.md` showing many launch-gating items still open.

To de-risk launch, we should treat the checklist as the source of truth for next actions.

## Execution artifact

- 10-day execution board to move 17/36 → 22/36: `docs/ten-day-execution-board.md`

## Priority order (next 2 weeks)

1. **Close observability and SLO gaps first**
   - Define SLOs for ingest success, generation success, and p95 processing time.
   - Emit queue depth, per-stage latency, failure-rate, and retry metrics.
   - Add alerting for sustained failures and queue backlog.
   - Publish one dashboard that lets on-call identify the failing pipeline stage in <5 minutes.

2. **Run reliability drills with evidence**
   - Execute a staged backup/restore drill for Postgres + object storage.
   - Execute a migration rollback drill against staging.
   - Capture timings, commands, and integrity checks; attach evidence links in checklist.

3. **Finish mobile MVP UX path**
   - Deliver end-to-end first-time flow: Course → Preset → Upload/Record → Process status → Review → Export.
   - Add progress, retries, and stage-level failure messaging.

4. **Complete security/compliance baseline**
   - Canonical secrets-management guidance per deploy target.
   - PII policy for transcripts/artifacts.
   - Lecture/course deletion workflow with auditability.
   - Dependency + container vulnerability scans as required CI gates.

5. **Prove launch gates with synthetic canaries**
   - Add scheduled ingest→transcribe→generate→export canary job(s).
   - Wire canary outcomes to alerts and dashboards.
   - Require green canary runs in launch decision checklist.

## Week-by-week execution slices

### Week 1 (ops first)
- Days 1–2: SLO definitions + metrics instrumentation.
- Day 3: dashboards.
- Day 4: alerting and alert-route verification.
- Day 5: backup/restore and rollback drills + evidence.

### Week 2 (risk burn-down)
- Day 6: secrets and configuration hardening docs.
- Day 7: vulnerability scanning in CI.
- Day 8: synthetic canary implementation + telemetry.
- Day 9: checklist evidence pass and closure.
- Day 10: overflow and go/no-go prep.

## Definition of "next milestone complete"

Mark this plan complete when all are true:
- Checklist progress reaches **at least 22/36 items (~61%)**.
- All observability items are checked with live links to dashboards and alert policies.
- Backup/restore + rollback drills are evidenced with dated staging outputs.
- At least one mobile platform demonstrates full first-time flow without terminal access.
- Canary jobs run on schedule and produce alertable pass/fail telemetry.

## Operating rule

When status documents disagree, default to the launch checklist and attached evidence rather than summary claims.
