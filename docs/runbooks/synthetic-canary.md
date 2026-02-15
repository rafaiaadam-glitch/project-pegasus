# Synthetic Canary Runbook

This runbook defines how to continuously verify the critical pipeline path:

`ingest -> transcribe -> generate -> export`

## Script

Use the executable canary script:

```bash
scripts/canary_pipeline.sh
```

The script performs:
1. `GET /health`
2. `POST /lectures/ingest`
3. `POST /lectures/{lecture_id}/transcribe`
4. `POST /lectures/{lecture_id}/generate`
5. `POST /lectures/{lecture_id}/export`
6. `GET /exports/{lecture_id}/{export_type}`

It exits non-zero on any stage failure/timeout so schedulers can alert on failures.

## Required environment

- `API_BASE_URL` (required)

## Optional environment

- `CANARY_TIMEOUT_SEC` (default `900`)
- `CANARY_POLL_INTERVAL_SEC` (default `5`)
- `CANARY_COURSE_ID` (default `canary-course`)
- `CANARY_LECTURE_ID` (default `canary-lecture-<timestamp>`)
- `CANARY_PRESET_ID` (default `exam-mode`)
- `CANARY_TRANSCRIBE_PROVIDER` (optional; if unset, API default is used)
- `CANARY_TRANSCRIBE_LANGUAGE` (optional)
- `CANARY_EXPORT_TYPE` (default `markdown`)
- `CANARY_CLEANUP_LECTURE` (`1/true` enables post-run `DELETE /lectures/{lecture_id}?purge_storage=true`)
- `CANARY_SUMMARY_FILE` (optional path to write JSON run summary)
- `CANARY_RESULT_WEBHOOK_URL` (optional URL to receive JSON run summary)
- `PLC_WRITE_API_TOKEN` or `CANARY_WRITE_API_TOKEN` (required if write auth is enabled)

## Local / manual execution

```bash
API_BASE_URL=http://127.0.0.1:8000 \
CANARY_TIMEOUT_SEC=300 \
CANARY_POLL_INTERVAL_SEC=2 \
CANARY_SUMMARY_FILE=/tmp/pegasus-canary-summary.json \
./scripts/canary_pipeline.sh
```

## Output contract

At completion, the script emits one line beginning with `CANARY_SUMMARY` and a JSON payload including:
- overall status (`passed` / `failed`)
- stage timings (`health`, `ingest`, `transcribe`, `generate`, `export`, `exportFetch`, `cleanup`) with cleanup timing captured before summary emission
- job IDs per stage
- failure stage/message (when failed)

This payload can be ingested by log-based metrics or forwarded via `CANARY_RESULT_WEBHOOK_URL`.

## Production scheduler examples

### Cron (VM / container host)

```cron
*/15 * * * * API_BASE_URL=https://pegasus-api.example.com CANARY_CLEANUP_LECTURE=1 CANARY_SUMMARY_FILE=/var/log/pegasus-canary-last.json /opt/pegasus/scripts/canary_pipeline.sh >> /var/log/pegasus-canary.log 2>&1
```

### Cloud Scheduler (HTTP-triggered job wrapper)

Wrap the script in a Cloud Run job and schedule every 15 minutes. Alert when:
- 2 consecutive runs fail, or
- failure ratio exceeds 20% over 1 hour.

## Alert policy guidance

Minimum alerts:
1. **Canary hard down**: no successful run for 30 minutes.
2. **Canary degraded**: >= 2 failures in a row.
3. **Canary latency SLO**: p95 run duration exceeds `CANARY_TIMEOUT_SEC * 0.8`.

## Operational notes

- Keep canary data isolated via dedicated `CANARY_COURSE_ID`.
- Prefer `CANARY_CLEANUP_LECTURE=1` in production schedules to avoid data buildup.
- If failures occur, inspect:
  - `/jobs/{job_id}` history for failing stage
  - worker logs for queue and provider errors
  - storage existence for exported artifacts

## Regression tests

- Success-path simulation: `./scripts/test_canary_pipeline_http.sh`
- Failure-path simulation: `./scripts/test_canary_pipeline_http_failure.sh`

Both run fully local using fake HTTP servers and verify summary payload behavior.
