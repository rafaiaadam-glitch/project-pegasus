# PLC MVP → v1 Launch Checklist

This checklist translates the current project state into a practical path to a shippable v1.

Use this as the default execution plan unless a milestone-specific roadmap supersedes it.

Status policy: checkboxes represent launch-readiness for the specific item (implementation + required operational artifacts where applicable).

---

## 1) Must-ship backend hardening

- [x] Add auth for write endpoints (`/lectures/*` POST routes)
- [x] Add API rate limiting and request size limits for ingest/transcript paths
- [x] Add structured logging (request IDs, lecture IDs, job IDs) across API and worker
- [ ] Add dead-letter / failed-job replay workflow for queue processing *(failed-job replay is implemented; dead-letter queue/runbook still pending)*
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
- [ ] Enforce retention lifecycle for raw uploads and intermediate artifacts
- [x] Add integrity checks for artifact files referenced in DB records

**Definition of done:**
- restore drill completes in staging
- retention policy is automated (not manual)

---

## 3) Pipeline quality gates

- [x] Add golden-output regression snapshots for each preset mode
- [x] Add schema drift CI check against `schemas/`
- [ ] Add thread continuity scoring checks (cross-lecture consistency)
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

- [x] Define SLOs (ingest success, generation success, p95 processing time) → `docs/observability-slos.md`
- [x] Emit metrics for queue depth, job latency, failure rate, retries *(queue depth, failure rate, replay-count, and latency exposed at `/metrics/operational`; retry-attempt metric still pending)*
- [ ] Add alerting for sustained failure spikes and queue backlogs
- [ ] Add dashboards for per-stage pipeline timings

**Definition of done:**
- on-call can identify failing stage within 5 minutes

---

## 6) Security, privacy, and compliance baseline

- [ ] Add secrets management guidance for each deploy target
- [ ] Add PII handling policy for transcripts and generated artifacts
- [ ] Add data deletion endpoint/workflow per lecture/course
- [ ] Add dependency and container vulnerability scanning in CI

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
- [ ] Incident response runbook exists (queue outage, OpenAI outage, storage outage)
- [ ] Monitoring + alerting verified by synthetic canary jobs

---

## Current completion snapshot (checklist-only)

- Total launch checklist items: **36**
- Items marked complete: **11**
- Items remaining: **25**
- Completion: **31%**

> Scope note: this percentage is checklist-tracking only and does not represent product quality or effort-weighted progress.

---

## Suggested execution order (highest ROI)

1. Backend hardening
2. Observability/SLOs
3. Mobile UX completion
4. Deployment readiness
5. Security/privacy baseline
6. Final launch gate run

This sequence minimizes launch risk by first stabilizing the processing core and operational visibility before polishing distribution surfaces.

---


## Evidence map (implemented today)

Use this section to quickly verify which checked items are backed by code/tests.

Last verified by targeted test run in this repo: backend hardening + pipeline quality-gate tests.

- Write endpoint auth → `backend/tests/test_write_auth.py`
- Write rate limiting + upload size limits → `backend/tests/test_rate_limit.py`, `backend/tests/test_upload_limits.py`
- Idempotency keys/replay semantics → `backend/tests/test_idempotency.py`
- Failed-job replay endpoint (`POST /jobs/{job_id}/replay`) → `backend/tests/test_job_replay.py`
- Artifact path integrity checks (`GET /lectures/{lecture_id}/integrity`) → `backend/tests/test_integrity_endpoint.py`
- Golden-output preset snapshots → `pipeline/tests/test_preset_summary_snapshots.py` + `pipeline/tests/snapshots/`
- Schema drift checks → `pipeline/tests/test_schema_drift_check.py`
- Export quality threshold (`PLC_EXPORT_MIN_SUMMARY_SECTIONS`) → `backend/jobs.py`, `backend/tests/test_jobs.py`
- Operational metrics endpoint (`GET /metrics/operational`) → `backend/app.py`, `backend/tests/test_operational_metrics.py`, `backend/tests/test_operational_metrics_helpers.py`
- SLO baseline definition → `docs/observability-slos.md`

## Progress notes

### Completed in-repo
- Write endpoint auth, rate limits, idempotency support, and startup env validation are implemented and covered by backend tests.
- Integrity verification endpoint exists (`GET /lectures/{lecture_id}/integrity`) and has tests for missing/present storage paths.
- Pipeline quality gates include preset snapshots and schema drift checks under `pipeline/tests/`.
- Export quality threshold support is wired via `PLC_EXPORT_MIN_SUMMARY_SECTIONS`.

### Clarifications from review
- The queue recovery path currently supports **failed job replay** (`POST /jobs/{job_id}/replay`), but a dedicated dead-letter queue workflow and operational runbook are not complete yet.
- This checklist treats launch-readiness as requiring both implementation **and** operational readiness (runbooks/drills), so any item missing operational artifacts remains unchecked.

### Still open before launch
- Operational reliability runbooks (backup/restore, rollback, retention automation).
- Mobile UX completion for a no-terminal first-time flow.
- SLO definitions, dashboards, and alerting. *(core operational metrics endpoint now available)*
- Security/compliance baseline work and final launch gate rehearsal.
