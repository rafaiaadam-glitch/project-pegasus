# Observability SLOs (MVP → v1)

This runbook defines launch-gating SLOs for Pegasus API/worker operations.

## Scope

The SLOs in this document apply to production traffic for the core lecture pipeline:

1. ingest (`POST /lectures/ingest`)
2. generation (`POST /lectures/{lecture_id}/generate`)
3. end-to-end processing (`ingest -> transcribe -> generate -> export-ready`)

## Measurement window

- Rolling **30-day** SLO window.
- Reporting cadence: daily check + weekly review.

## SLO 1 — Ingest success rate

- **Target:** >= **99.5%** successful ingest requests over 30 days.
- **SLI numerator:** count of `POST /lectures/ingest` requests with 2xx status and persisted lecture/job IDs.
- **SLI denominator:** all valid ingest requests that passed auth and request validation.
- **Exclusions:** clearly client-cancelled requests and explicit load-test traffic.

### Error budget

- Allowed error budget: **0.5%** of qualifying ingest requests per 30 days.
- Burn policy:
  - 50% consumed in <15 days => trigger SEV-2 investigation.
  - 100% consumed before window end => freeze non-critical changes until stable.

## SLO 2 — Generation success rate

- **Target:** >= **99.0%** successful generation jobs over 30 days.
- **SLI numerator:** jobs that reach terminal `completed` for generation.
- **SLI denominator:** all generation jobs accepted into processing.
- **Exclusions:** user-initiated cancellations.

### Error budget

- Allowed error budget: **1.0%** of generation jobs per 30 days.
- Burn policy:
  - 50% consumed in <15 days => on-call + product review.
  - 100% consumed before window end => pause feature rollouts touching pipeline.

## SLO 3 — End-to-end p95 processing time

- **Target:** p95 ingest->export-ready latency <= **15 minutes** over 30 days.
- **SLI definition:** elapsed time between ingest acceptance timestamp and export-ready terminal state.
- **Denominator:** all successful end-to-end flows.

### Error budget

- Allowed latency budget: p95 may exceed 15 minutes for <=5% of daily slices in window.
- Burn policy:
  - 3 consecutive daily breaches => SEV-2, scale/tuning action required.
  - 5 daily breaches in any rolling 7-day period => SEV-1 launch risk.

## Alerting thresholds (minimum)

Wire alerting to these thresholds:

- ingest success drops below 99.5% (1h rolling)
- generation success drops below 99.0% (1h rolling)
- p95 end-to-end latency > 15 minutes (1h rolling)
- queue backlog above operational threshold for >15 minutes

## Ownership

- Primary DRI: Platform/SRE Lead
- Supporting DRIs: Backend Lead, QA Lead

## Evidence required for checklist closure

Before considering launch-gating observability complete:

- dashboard links for all three SLIs
- alert policy links and routed test-notification evidence
- dated weekly SLO review note in operational log

## Dashboard metric references

Use these exported metrics for dashboard panels:

- Queue backlog by status: `pegasus_queue_depth{status=...}`
- Job failure totals by stage: `pegasus_job_failures_total{job_type=...}`
- Retry totals by stage: `pegasus_job_retries_total{job_type=...}`
- Stage latency (avg/p95/max):
  - `pegasus_job_latency_ms_avg{job_type=...}`
  - `pegasus_job_latency_ms_p95{job_type=...}`
  - `pegasus_job_latency_ms_max{job_type=...}`

Recommended initial alert thresholds:

- Backlog alert: queued depth > 25 for 15m
- Failure spike alert: failed status events ratio > 5% for 15m by `job_type`
- Latency alert: p95 stage latency sustained above baseline for 15m
