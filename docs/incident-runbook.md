# Incident Response Runbook (MVP)

This runbook covers the highest-risk MVP outages: queue, OpenAI generation, and storage.

## Severity levels

- **SEV-1**: End-to-end flow is down for most users (ingest/transcribe/generate/export blocked).
- **SEV-2**: One pipeline stage degraded or delayed (e.g., generation failures spike).
- **SEV-3**: Partial feature issue with workaround available.

## Global first response (0-5 min)

1. Confirm impact in API health/readiness and latest failed jobs.
2. Identify failing stage (`transcription`, `generation`, `export`) from lecture/job progress endpoints.
3. Notify stakeholders with start time, blast radius, and probable subsystem.
4. Apply immediate mitigation for user-facing stability (pause retries / fail fast / route to fallback mode).

## Queue outage (Redis/RQ)

### Signals
- `GET /health/ready` fails queue check.
- Job backlog grows and `queued` jobs stop advancing.

### Triage
1. Validate `REDIS_URL` connectivity from API and worker.
2. Check worker process/container health and restart if needed.
3. Verify enqueue path still succeeds from API logs.

### Mitigation
- Temporarily enable inline jobs for API-only emergency mode (`PLC_INLINE_JOBS=true`) if worker/Redis remains unavailable.
- Replay failed jobs after queue recovery using `POST /jobs/{job_id}/replay`.

### Recovery criteria
- New jobs transition from queued -> running -> completed.
- Backlog returns to normal operating range.

## OpenAI outage / generation failures

### Signals
- Generation stage failures spike.
- Retry logs show repeated 429/5xx responses.

### Triage
1. Validate `OPENAI_API_KEY` and model config.
2. Inspect retry/error patterns and failure rates.
3. Confirm non-LLM stages still pass.

### Mitigation
- Switch to lower-latency fallback model if configured.
- Temporarily pause generation enqueue while ingest/transcribe continues.
- Replay failed generation jobs after provider recovery.

### Recovery criteria
- Generation success ratio returns above target.
- p95 generation latency back within SLO budget.

## Storage outage (local/S3)

### Signals
- Readiness storage check fails.
- Integrity endpoint reports missing/unreadable files.
- Export downloads return 404/500.

### Triage
1. Confirm storage credentials/config and bucket/path availability.
2. Check write permissions and disk space (local mode).
3. Validate object existence for recent artifacts/exports.

### Mitigation
- Stop export job enqueue if writes are failing.
- Preserve DB metadata; avoid destructive cleanup until storage restored.
- Re-run exports for affected lectures once storage is healthy.

### Recovery criteria
- New writes succeed.
- Integrity checks show zero missing critical paths for new jobs.

## Post-incident follow-up

- Create timeline (detection -> mitigation -> resolution).
- Document root cause and prevention actions.
- Add/adjust alert thresholds and synthetic canary assertions.
- Add tests for discovered regression path.
