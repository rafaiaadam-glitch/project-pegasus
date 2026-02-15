# Synthetic Canary Runbook

This runbook defines how to execute and operationalize the Pegasus synthetic canary.

## Purpose

Continuously verify the critical path works end-to-end:

1. `POST /lectures/ingest`
2. `POST /lectures/{lecture_id}/transcribe`
3. `POST /lectures/{lecture_id}/generate`
4. `POST /lectures/{lecture_id}/export`
5. `GET /lectures/{lecture_id}/integrity`

The canary fails fast if any stage fails or exceeds the timeout.

## Script

- Local/CI script: `scripts/run_synthetic_canary.py`
- GitHub Actions schedule: `.github/workflows/synthetic-canary.yml` (hourly + manual trigger)

## Required configuration

### GitHub Actions Secrets

- `PEGASUS_CANARY_API_URL`: base URL for target environment (for example, staging API URL)
- `PEGASUS_CANARY_API_TOKEN`: bearer token if `PLC_WRITE_API_TOKEN` is enforced

### GitHub Actions Variables (optional overrides)

- `PEGASUS_CANARY_STT_PROVIDER` (default: `google`)
- `PEGASUS_CANARY_STT_MODEL` (default: `latest_long`)
- `PEGASUS_CANARY_LLM_PROVIDER` (default: `gemini`)
- `PEGASUS_CANARY_LLM_MODEL` (default: `gemini-1.5-flash`)

## Local execution

```bash
export PEGASUS_API_URL="https://your-api.example.com"
export PLC_WRITE_API_TOKEN="...optional..."
python scripts/run_synthetic_canary.py
```

Optional custom timeout/polling:

```bash
python scripts/run_synthetic_canary.py --timeout-sec 1200 --poll-sec 10
```

## Output

The script prints a JSON payload containing:

- overall `status` (`ok` or `failed`)
- stage-level job payloads
- `integrity` and `summary` responses
- total `durationSec`

In GitHub Actions, this is saved as `canary-result.json` and uploaded as an artifact.

## Alerting guidance

- Configure alerting on workflow failures for `Synthetic Canary`.
- Route failures to the same on-call channel used for pipeline incidents.
- During launch gating, require multiple consecutive green runs before marking checklist complete.

## Operational notes

- Canary data is persisted as synthetic lectures; periodically clean these by filtering IDs that start with `canary-`.
- If failures are intermittent, inspect the stage in `canary-result.json` and correlate with `/ops/metrics` and worker logs.
