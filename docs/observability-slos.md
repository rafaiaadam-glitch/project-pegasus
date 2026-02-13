# PLC MVP Observability & SLO Baseline

This document defines the minimum observability contract for MVP launch-readiness.

## Scope

These SLOs cover the backend processing path from ingestion through export for production traffic.

Data sources:
- `GET /metrics/operational` for queue depth, job outcomes, replay counts, and latency.
- `GET /health/ready` for dependency readiness (database, queue, storage).

## SLOs

### 1) Ingest success rate
- **SLI**: successful ingest responses / total ingest requests.
- **Target**: **≥ 99.0%** over rolling 7 days.
- **Measurement**: API logs by route `POST /lectures/ingest` and status family.

### 2) Generation success rate
- **SLI**: generation jobs with `status=completed` / total generation jobs.
- **Target**: **≥ 97.0%** over rolling 7 days.
- **Measurement**: `/metrics/operational.jobs` + jobs table query by `job_type=generation`.

### 3) Export success rate
- **SLI**: export jobs with `status=completed` / total export jobs.
- **Target**: **≥ 98.0%** over rolling 7 days.
- **Measurement**: jobs table query by `job_type=export`.

### 4) Processing latency p95
- **SLI**: p95 of completed job latency in milliseconds.
- **Target**: **≤ 15 minutes** for generation jobs, rolling 24 hours.
- **Measurement**: `/metrics/operational.jobs.latencyMs.p95` and job-type filtered queries.

### 5) Readiness availability
- **SLI**: successful `200` responses from `/health/ready`.
- **Target**: **≥ 99.5%** monthly.
- **Measurement**: synthetic readiness probes every minute.

## Early warning thresholds (pre-SLO breach)

Page/alert when any is sustained for 10+ minutes:
- Queue depth `> 100`.
- Failure rate in `/metrics/operational.jobs.failureRate` `> 0.10`.
- `/health/ready` returns `503` for 3 consecutive checks.

## Incident labels

Use these labels in incident tickets/runbooks:
- `queue-backlog`
- `generation-failure-spike`
- `storage-readiness-failure`
- `database-readiness-failure`

## MVP caveats

- Retry-attempt counts are not yet exposed as a first-class metric in `/metrics/operational`.
- Dashboard and alert wiring is tracked separately in `docs/mvp-launch-checklist.md`.
