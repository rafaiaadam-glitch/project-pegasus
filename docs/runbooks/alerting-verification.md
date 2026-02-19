# Alerting verification runbook (failure spikes + queue backlog)

This runbook covers launch checklist item:

- "Add alerting for sustained failure spikes and queue backlogs"

## Policy source

- Prometheus rules: `ops/monitoring/prometheus-alert-rules.yml`
- Rule group: `pegasus-pipeline-alerts`

## Alert thresholds

1. `PegasusQueueBacklogSustained`
   - Trigger when `sum(pegasus_queue_depth) > 25` for 15 minutes.
2. `PegasusFailureRateSpike`
   - Trigger when failed/(failed+completed) job ratio exceeds 10% for 10 minutes.
3. `PegasusGenerationFailureBurst`
   - Trigger when 5+ `generate` jobs fail within 10 minutes.

## Validation commands

Use these commands in staging with the metrics endpoint reachable:

```bash
# 1) Validate rule file shape and required alert names.
pytest backend/tests/test_alert_rules_config.py

# 2) View live prometheus metrics payload.
curl -s http://localhost:8000/ops/metrics/prometheus | head -n 120

# 3) Check JSON snapshot including queue depth.
curl -s http://localhost:8000/ops/metrics | jq .
```

## Synthetic trigger recipe (staging)

1. Pause or scale worker deployment to zero.
2. Submit >25 jobs via ingest endpoint.
3. Confirm queue depth remains above threshold for at least 15 minutes.
4. Verify `PegasusQueueBacklogSustained` fires and routes to on-call.

Failure-rate spike test:

1. Configure model provider env var to a known-invalid value in staging worker only.
2. Submit at least 20 generation jobs.
3. Confirm failure ratio stays >10% for >=10 minutes.
4. Verify `PegasusFailureRateSpike` alert fires and routes correctly.

## Evidence capture template

Record these 3 proof lines for checklist closure:

- **Endpoint/UI:** Alert policy loaded from `ops/monitoring/prometheus-alert-rules.yml` in staging monitoring stack.
- **Test:** `pytest backend/tests/test_alert_rules_config.py` + synthetic trigger command log.
- **Proof:** Screenshot/export of fired alert showing alert name, fired timestamp, and notification route.
