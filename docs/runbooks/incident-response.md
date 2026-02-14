# Incident Response Runbook (Queue, OpenAI, Storage)

This runbook defines first-response and recovery actions for the PLC pipeline's highest-impact outages.

## Scope

This runbook covers:
- Queue outage/backlog growth
- OpenAI outage or degraded model responses
- Object storage outage or persistent write/read failures

## Severity model

- **SEV-1**: Full production outage, critical-path processing unavailable for most users.
- **SEV-2**: Major degradation, retries/fallbacks partially working but SLOs at risk.
- **SEV-3**: Localized degradation with acceptable workaround.

Escalate to **SEV-1** when any of these hold for >15 minutes:
- ingest/generation success drops below 80%
- queue depth continuously increases with no successful drain
- export artifacts cannot be read or written for new jobs

## Common response workflow

1. **Acknowledge and classify severity** (SEV-1/2/3).
2. **Stabilize** by stopping harmful retries and preserving idempotency.
3. **Identify failing stage** (queue, OpenAI, storage).
4. **Mitigate** using outage-specific playbooks below.
5. **Recover** backlog with replay/batch tools.
6. **Validate** synthetic job completion end-to-end.
7. **Communicate** status every 15 minutes until resolved.
8. **Record timeline** and post-incident action items.

---

## A) Queue outage / backlog incident

### Signals
- Queue depth increasing for 10+ minutes
- Spike in dead-letter count
- Worker restart loops / inability to claim jobs

### Immediate actions
1. Check API and worker health endpoints.
2. Confirm broker connectivity and credentials.
3. Pause non-critical enqueue sources if backlog is runaway.
4. Keep idempotency enforcement enabled (do not bypass duplicate guards).

### Recovery
1. Restore queue connectivity and worker consumption.
2. Replay failed single jobs as needed:
   - `POST /jobs/{job_id}/replay`
3. For dead-letter batches:
   - inspect: `GET /jobs/dead-letter`
   - replay: `POST /jobs/dead-letter/replay`
4. Monitor drain trend until backlog is stable.

### Exit criteria
- Backlog decreasing steadily for 30 minutes
- New jobs transition through all stages successfully
- Dead-letter replay completes without new systemic failures

---

## B) OpenAI outage / degraded responses

### Signals
- Sustained 5xx/429 from provider
- Latency spikes causing queue timeout churn
- Increased schema/quality-gate failures in generation stage

### Immediate actions
1. Confirm provider status page / regional advisories.
2. Increase retry backoff and reduce concurrent generation throughput.
3. Temporarily prioritize essential presets/exports if needed.
4. Preserve failed payload metadata for deterministic replay.

### Recovery
1. Resume standard concurrency after provider stabilizes.
2. Replay failed generation/export jobs through replay endpoints.
3. Verify quality threshold checks pass on synthetic and recent jobs.

### Exit criteria
- Provider error rate returns to baseline
- Generation stage success rate recovers to normal operating band
- Replay queue drains without renewed failure spike

---

## C) Storage outage / read-write failures

### Signals
- Upload failures on ingest paths
- Export write failures or missing artifact reads
- Integrity endpoint reports missing paths for fresh artifacts

### Immediate actions
1. Validate storage endpoint health and credentials.
2. Confirm bucket policies, lifecycle, and encryption settings have not regressed.
3. Pause destructive cleanup jobs if storage metadata is inconsistent.
4. If required, switch to read-only mode for review endpoints until writes recover.

### Recovery
1. Restore storage access.
2. Re-run integrity checks for affected lectures.
3. Replay failed export/generation tasks once artifact paths are writable.
4. Confirm backup snapshots are healthy after incident.

### Exit criteria
- New uploads and exports succeed consistently
- Integrity checks pass for incident window samples
- No sustained storage 5xx/timeout errors

---

## Verification checklist (post-mitigation)

- Submit one synthetic lecture job end-to-end (ingest → transcribe → generate → export)
- Confirm artifact integrity endpoint passes for the synthetic lecture
- Confirm no elevated dead-letter growth for 30 minutes
- Log incident summary and owner-assigned follow-ups

## Communications template

- **Status**: investigating | mitigating | monitoring | resolved
- **Impact**: affected stages/users
- **Scope**: queue | OpenAI | storage | mixed
- **ETA**: next update time
- **Next actions**: replay, scaling, fallback

## Related docs

- `docs/runbooks/dead-letter-queue.md`
- `docs/runbooks/backup-restore.md`
- `docs/runbooks/migration-rollback.md`
- `docs/deploy.md`
