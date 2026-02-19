# Pipeline timing dashboard runbook

This runbook covers launch checklist item:

- "Add dashboards for per-stage pipeline timings"

## Dashboard source

- Grafana dashboard JSON: `ops/monitoring/grafana-pipeline-dashboard.json`
- Dashboard UID: `pegasus-pipeline-ops`

## Required panels

1. Queue depth (all statuses)
2. Per-stage average latency (ingest, transcribe, generate, export)
3. Per-stage max latency (ingest, transcribe, generate, export)
4. Failure rate by stage (15m)
5. Retries by stage (15m)

## Validation commands

```bash
# Validate dashboard JSON and required panel titles/queries.
pytest backend/tests/test_monitoring_assets.py

# Inspect prometheus payload used by the dashboard.
curl -s http://localhost:8000/ops/metrics/prometheus | head -n 120
```

## Evidence capture template

Record these 3 proof lines for checklist closure:

- **Endpoint/UI:** Grafana dashboard imported from `ops/monitoring/grafana-pipeline-dashboard.json`.
- **Test:** `pytest backend/tests/test_monitoring_assets.py`.
- **Proof:** Screenshot of dashboard with all required panels and a timestamp.
