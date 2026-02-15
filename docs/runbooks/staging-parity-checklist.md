# Staging Environment Parity Checklist

Use this checklist before release-candidate validation. The goal is to ensure staging behavior matches production for critical path workflows.

## 1) Runtime + infrastructure parity

- [ ] Same backend image family and startup commands as production (`backend/Dockerfile`, API + worker).
- [ ] Same Postgres major version as production.
- [ ] Same Redis major version as production.
- [ ] Same storage mode as production (`local`/`s3`/`gcs`) with equivalent permissions.
- [ ] API + worker use identical queue/storage/LLM/transcription configuration classes.

## 2) Configuration parity

- [ ] `DATABASE_URL` points to staging DB (never production).
- [ ] `REDIS_URL` points to staging queue (never production).
- [ ] `STORAGE_MODE` and bucket/prefix values match production pattern.
- [ ] `PLC_LLM_PROVIDER` and model defaults match production intent.
- [ ] `PLC_GCP_STT_MODEL` and `PLC_STT_LANGUAGE` match production intent.
- [ ] `PLC_WRITE_API_TOKEN` enabled and validated in staging.

## 3) Operational controls parity

- [ ] `/health/ready` probes configured at platform level.
- [ ] Metrics endpoints (`/ops/metrics`, `/ops/metrics/prometheus`) reachable in staging.
- [ ] Alert routes configured against staging signal sources (where applicable).
- [ ] Dead-letter replay endpoints tested with a synthetic failed job.

## 4) Data safety + compliance parity

- [ ] Retention job configuration mirrors production (`backend.retention`).
- [ ] Deletion workflows verified (`DELETE /lectures/{id}`, `DELETE /courses/{id}`).
- [ ] Secrets are sourced from provider-managed secret stores (not plaintext env files).
- [ ] Access controls follow least privilege for service accounts and operators.

## 5) Validation evidence (attach per release candidate)

- [ ] Worker/queue smoke output attached (`scripts/smoke_worker_queue.sh`).
- [ ] Readiness checks and deploy logs attached.
- [ ] One end-to-end ingest→transcribe→generate→export run attached.
- [ ] Rollback rehearsal reference attached (`docs/runbooks/migration-rollback.md`).

## Sign-off

- Release candidate:
- Date (UTC):
- Operator:
- Notes/exceptions:
