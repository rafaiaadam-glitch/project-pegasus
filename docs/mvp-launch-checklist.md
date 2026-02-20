# PLC MVP → v1 Launch Checklist

This checklist translates the current project state into a practical path to a shippable v1.

Use this as the default execution plan unless a milestone-specific roadmap supersedes it.

Status policy: checkboxes represent launch-readiness for the specific item (implementation + required operational artifacts where applicable).

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

- [x] Define SLOs (ingest success, generation success, p95 processing time)
- [x] Emit metrics for queue depth, job latency, failure rate, retries
- [ ] Add alerting for sustained failure spikes and queue backlogs
- [ ] Add dashboards for per-stage pipeline timings

**Definition of done:**
- on-call can identify failing stage within 5 minutes

---

## 6) Security, privacy, and compliance baseline

- [x] Add secrets management guidance for each deploy target
- [x] Add PII handling policy for transcripts and generated artifacts
- [x] Add data deletion endpoint/workflow per lecture/course
- [ ] Add dependency and container vulnerability scanning in CI

**Definition of done:**
- documented deletion flow and auditability for destructive operations

---

## 7) Deployment readiness

- [x] Publish one canonical deployment guide for API + worker + storage
- [x] Add health/readiness checks to platform configs with sane thresholds
- [x] Add staging environment parity checklist
- [x] Add release checklist with rollback procedure

**Definition of done:**
- staged release and rollback completed successfully at least once

---

## 8) v1 launch gating checklist

Before launch, all must be true:

- [ ] Critical-path integration tests pass (ingest → transcribe → generate → export)
- [ ] API and worker deploy from main with reproducible config
- [ ] At least one mobile build (iOS/Android) validated end-to-end against staging
- [x] Incident response runbook exists (queue outage, OpenAI outage, storage outage)
- [ ] Monitoring + alerting verified by synthetic canary jobs

---

## Current completion snapshot (checklist-only)

- Total launch checklist items: **36**
- Items marked complete: **22**
- Items remaining: **14**
- Completion: **61%**

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

## 2-week acceleration plan

- Execution plan to move from 36% to ~60% quickly: `docs/two-week-36-to-60-plan.md`

---


## Evidence map (implemented today)

Use this section to quickly verify which checked items are backed by code/tests.

Last verified by targeted test run in this repo: backend hardening + pipeline quality-gate tests.

- Write endpoint auth → `backend/tests/test_write_auth.py`
- Write rate limiting + upload size limits → `backend/tests/test_rate_limit.py`, `backend/tests/test_upload_limits.py`
- Idempotency keys/replay semantics → `backend/tests/test_idempotency.py`
- Failed-job replay endpoint (`POST /jobs/{job_id}/replay`) → `backend/tests/test_job_replay.py`
- Dead-letter listing + batch replay endpoints (`GET /jobs/dead-letter`, `POST /jobs/dead-letter/replay`) → `backend/tests/test_dead_letter_workflow.py`, `docs/runbooks/dead-letter-queue.md`
- Artifact path integrity checks (`GET /lectures/{lecture_id}/integrity`) → `backend/tests/test_integrity_endpoint.py`
- Backup/restore procedure runbook → `docs/runbooks/backup-restore.md`
- Migration rollback guidance runbook → `docs/runbooks/migration-rollback.md`
- Retention cleanup automation (`python -m backend.retention`) → `backend/retention.py`, `backend/tests/test_retention.py`, `docs/deploy.md`
- Golden-output preset snapshots → `pipeline/tests/test_preset_summary_snapshots.py` + `pipeline/tests/snapshots/`
- Schema drift checks → `pipeline/tests/test_schema_drift_check.py`
- Thread continuity scoring checks → `pipeline/thread_continuity.py`, `pipeline/tests/test_thread_continuity_scoring.py`
- Export quality threshold (`PLC_EXPORT_MIN_SUMMARY_SECTIONS`) → `backend/jobs.py`, `backend/tests/test_jobs.py`
- Incident response runbook (queue/OpenAI/storage) → `docs/runbooks/incident-response.md`
- SLO definitions (ingest success, generation success, p95 processing time) → `docs/runbooks/observability-slos.md`
- Metrics endpoints + instrumentation (JSON + Prometheus for queue depth, latency/failures/retries) → `backend/observability.py`, `backend/app.py`, `backend/jobs.py`, `backend/tests/test_observability_metrics.py`
- Alert policy baseline for sustained queue backlog + failure spikes → `ops/monitoring/prometheus-alert-rules.yml`, `docs/runbooks/alerting-verification.md`, `backend/tests/test_alert_rules_config.py`
- Dashboard baseline for per-stage pipeline timings → `ops/monitoring/grafana-pipeline-dashboard.json`, `docs/runbooks/pipeline-dashboard.md`, `backend/tests/test_monitoring_assets.py`
- Secrets management guidance per deploy target (Render/Railway/Fly/GCP/local) → `docs/runbooks/secrets-management.md`
- Deletion workflow with auditability (`DELETE /lectures/{lecture_id}`, `DELETE /courses/{course_id}`, `GET /ops/deletion-audit`) → `backend/app.py`, `backend/db.py`, `backend/migrations/002_deletion_audit.sql`, `backend/tests/test_delete_workflow.py`
- PII handling policy for transcript/artifact data → `docs/PII_HANDLING_POLICY.md`
- Canonical deployment guide (Cloud Run production) → `docs/deployment-guide.md`
- Health/readiness/liveness probes + Cloud Run config → `backend/app.py` (`/health/live`), `cloudbuild.yaml` (startup + liveness probes, scaling bounds)
- Staging environment parity checklist → `docs/staging-parity-checklist.md`
- Release checklist with rollback procedure → `docs/release-checklist.md`

## Progress notes

### Completed in-repo
- Write endpoint auth, rate limits, idempotency support, and startup env validation are implemented and covered by backend tests.
- Integrity verification endpoint exists (`GET /lectures/{lecture_id}/integrity`) and has tests for missing/present storage paths.
- Pipeline quality gates include preset snapshots and schema drift checks under `pipeline/tests/`.
- Export quality threshold support is wired via `PLC_EXPORT_MIN_SUMMARY_SECTIONS`.

### Clarifications from review
- The queue recovery path supports single-job replay (`POST /jobs/{job_id}/replay`) and dead-letter batch workflows (`GET /jobs/dead-letter`, `POST /jobs/dead-letter/replay`) with an operations runbook under `docs/runbooks/dead-letter-queue.md`.
- This checklist treats launch-readiness as requiring both implementation **and** operational readiness (runbooks/drills), so any item missing operational artifacts remains unchecked.

### Still open before launch
- Complete backup/restore and rollback drills in staging (runbooks are documented; drill evidence still needed).
- Mobile UX completion for a no-terminal first-time flow.
- Dashboards and alerting.
- Security/compliance baseline work and final launch gate rehearsal.
