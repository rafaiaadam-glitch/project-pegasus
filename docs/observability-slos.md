# Observability & SLO Baseline (MVP)

This baseline defines the minimum service-level objectives and instrumentation needed before v1 launch.

## SLOs

### 1) Ingest success rate
- **SLI**: successful `POST /lectures/ingest` responses / total ingest requests.
- **Target**: **>= 99.0%** over 7 days.

### 2) Generation success rate
- **SLI**: completed generation jobs / total generation jobs.
- **Target**: **>= 97.0%** over 7 days.

### 3) End-to-end pipeline latency
- **SLI**: time from ingest accepted to export completed for successful jobs.
- **Target**: **p95 <= 10 minutes** over 24h.

## Required metrics

- Queue depth (`queued` jobs count).
- Job latency by stage (`transcription`, `generation`, `export`).
- Job failure rate by stage and error class.
- Retry count and retry-exhausted count.
- API write error rate (`4xx`, `5xx`) on ingest/transcribe/generate/export.

## Alert recommendations

- **Critical**: generation failure rate > 10% for 10 min.
- **Warning**: queue depth > 100 for 15 min.
- **Critical**: readiness check failing for 5 min.
- **Warning**: p95 end-to-end latency > 10 min for 30 min.

## Dashboard sections

1. Request volume and error rates (write endpoints).
2. Queue depth and dequeue throughput.
3. Per-stage success/failure and latency percentiles.
4. Replay volume and failure recovery trend.
5. Storage integrity check failures.

## Operational cadence

- Daily: review failures/retries and queue backlog trends.
- Weekly: review SLO compliance and top incident causes.
- Release day: run synthetic canary and verify alerts fire as expected.
