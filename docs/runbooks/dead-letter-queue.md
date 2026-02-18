# Dead-letter queue and failed-job replay runbook

This runbook covers how to inspect and replay failed background jobs.

## 1) Inspect failed jobs

List all failed jobs:

```bash
curl -s http://localhost:8000/jobs/dead-letter | jq
```

Filter by lecture:

```bash
curl -s "http://localhost:8000/jobs/dead-letter?lecture_id=<lecture-id>" | jq
```

Filter by job type:

```bash
curl -s "http://localhost:8000/jobs/dead-letter?job_type=generation" | jq
```

## 2) Replay one failed job

Use the existing single-job replay endpoint:

```bash
curl -X POST http://localhost:8000/jobs/<job-id>/replay
```

## 3) Replay a dead-letter batch

Replay all failed jobs:

```bash
curl -X POST http://localhost:8000/jobs/dead-letter/replay
```

Replay up to N jobs in one run:

```bash
curl -X POST "http://localhost:8000/jobs/dead-letter/replay?limit=10"
```

Replay failed jobs for a specific lecture:

```bash
curl -X POST "http://localhost:8000/jobs/dead-letter/replay?lecture_id=<lecture-id>"
```

## 4) Verify outcomes

Check job status:

```bash
curl -s http://localhost:8000/jobs/<new-job-id> | jq
```

Check lecture progress:

```bash
curl -s http://localhost:8000/lectures/<lecture-id>/progress | jq
```

## Notes

- Batch replay only attempts jobs currently in `failed` status.
- Unsupported job types are skipped and returned in `skippedJobs`.
- If write auth is enabled (`PLC_WRITE_API_TOKEN`), include `Authorization: Bearer <token>` for replay endpoints.
