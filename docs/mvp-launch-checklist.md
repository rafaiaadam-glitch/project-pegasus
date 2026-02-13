# PLC MVP → v1 Launch Checklist

This checklist translates the current project state into a practical path to a shippable v1.

Use this as the default execution plan unless a milestone-specific roadmap supersedes it.

---

## 1) Must-ship backend hardening

- [x] Add auth for write endpoints (`/lectures/*` POST routes)
- [x] Add API rate limiting and request size limits for ingest/transcript paths
- [x] Add structured logging (request IDs, lecture IDs, job IDs) across API and worker
- [x] Add dead-letter / failed-job replay workflow for queue processing
- [x] Add idempotency keys for ingest/generate/export operations
- [x] Validate all required env vars at startup with clear failure messages

**Definition of done:**
- 401/403 behavior is tested for protected endpoints
- replaying a failed job is documented and tested
- duplicate generate/export requests do not create inconsistent states

---

## 2) Data & storage reliability

- [ ] Add backup/restore procedure for Postgres and object storage
- [ ] Add migration rollback guidance for production incidents
- [x] Enforce retention lifecycle for raw uploads and intermediate artifacts
- [x] Add integrity checks for artifact files referenced in DB records

**Definition of done:**
- restore drill completes in staging
- retention policy is automated (not manual)

---

## 3) Pipeline quality gates

- [x] Add golden-output regression snapshots for each preset mode
- [x] Add schema drift CI check against `schemas/`
- [x] Add thread continuity scoring checks (cross-lecture consistency)
- [x] Add minimum quality thresholds for generated artifacts before export

**Definition of done:**
- CI fails on schema-breaking output changes
- preset differences are verified in automated tests

---

## 4) Mobile product completion (MVP UX)

- [ ] Replace scaffold-only flow with production navigation and error states
- [ ] Add upload/record progress indicators and retry UX
- [ ] Add per-lecture status timeline and stage-level failure messaging
- [ ] Add artifact review screens tuned for revision workflows
- [ ] Add export download/open/share affordances

**Definition of done:**
- a first-time user can complete Course → Preset → Upload → Process → Review → Export with no terminal access

---

## 5) Observability & SLOs

- [ ] Define SLOs (ingest success, generation success, p95 processing time)
- [ ] Emit metrics for queue depth, job latency, failure rate, retries
- [ ] Add alerting for sustained failure spikes and queue backlogs
- [ ] Add dashboards for per-stage pipeline timings

**Definition of done:**
- on-call can identify failing stage within 5 minutes

---

## 6) Security, privacy, and compliance baseline

- [ ] Add secrets management guidance for each deploy target
- [ ] Add PII handling policy for transcripts and generated artifacts
- [x] Add data deletion endpoint/workflow per lecture/course
- [x] Add dependency and container vulnerability scanning in CI

**Definition of done:**
- documented deletion flow and auditability for destructive operations

---

## 7) Deployment readiness

- [ ] Publish one canonical deployment guide for API + worker + storage
- [ ] Add health/readiness checks to platform configs with sane thresholds
- [ ] Add staging environment parity checklist
- [ ] Add release checklist with rollback procedure

**Definition of done:**
- staged release and rollback completed successfully at least once

---

## 8) v1 launch gating checklist

Before launch, all must be true:

- [ ] Critical-path integration tests pass (ingest → transcribe → generate → export)
- [ ] API and worker deploy from main with reproducible config
- [ ] At least one mobile build (iOS/Android) validated end-to-end against staging
- [x] Incident response runbook exists (queue outage, OpenAI outage, storage outage)
- [x] Monitoring + alerting verified by synthetic canary jobs

---

## Suggested execution order (highest ROI)

1. Backend hardening
2. Observability/SLOs
3. Mobile UX completion
4. Deployment readiness
5. Security/privacy baseline
6. Final launch gate run

This sequence minimizes launch risk by first stabilizing the processing core and operational visibility before polishing distribution surfaces.
