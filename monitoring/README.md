# Pegasus Gemini 3 Pro Monitoring Setup

This directory contains Cloud Monitoring configurations for production observability of the Gemini 3 Pro reasoning model.

## Quick Start

### 1. Deploy Monitoring Dashboard

**Option A: Using gcloud CLI**
```bash
gcloud monitoring dashboards create --config-from-file=gemini-dashboard.json
```

**Option B: Manual Import**
1. Open [Google Cloud Console - Monitoring Dashboards](https://console.cloud.google.com/monitoring/dashboards)
2. Click "Create Dashboard" → "Import from JSON"
3. Paste contents of `gemini-dashboard.json`
4. Click "Save"

### 2. Set Up SLO Alerts

**Option A: Using Terraform (Recommended)**
```bash
cd monitoring
terraform init
terraform plan -var="project_id=delta-student-486911-n5"
terraform apply -var="project_id=delta-student-486911-n5"
```

**Option B: Using gcloud CLI**
```bash
# Create each alert policy individually
gcloud alpha monitoring policies create --policy-from-file=alerts-slo.json
```

**Option C: Manual Creation**
1. Open [Google Cloud Console - Alerting](https://console.cloud.google.com/monitoring/alerting)
2. Click "Create Policy"
3. Use the conditions and thresholds documented in `alerts-slo.json`

### 3. Configure Notification Channels

Before alerts are useful, connect them to notification channels:

```bash
# List existing notification channels
gcloud alpha monitoring channels list

# Create email notification channel
gcloud alpha monitoring channels create \
  --display-name="Pegasus On-Call" \
  --type=email \
  --channel-labels=email_address=oncall@example.com

# Create Slack notification channel (requires Slack webhook URL)
gcloud alpha monitoring channels create \
  --display-name="Pegasus Slack Alerts" \
  --type=slack \
  --channel-labels=url=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Update Terraform variable with channel IDs
terraform apply \
  -var="project_id=delta-student-486911-n5" \
  -var='notification_channels=["projects/PROJECT_ID/notificationChannels/CHANNEL_ID"]'
```

## Metrics Reference

### Thinking Model Metrics (Gemini 3 Pro)

These metrics track the performance of reasoning-based LLM generation:

| Metric Name | Type | Description | SLO Target |
|-------------|------|-------------|------------|
| `pegasus_thinking_duration_seconds_avg` | Gauge | Average reasoning latency per request | p95 < 45s |
| `pegasus_thinking_duration_seconds_max` | Gauge | Maximum reasoning latency observed | < 120s |
| `pegasus_thinking_requests_total` | Counter | Total requests by model and status | Success rate > 98% |
| `pegasus_thinking_errors_total` | Counter | Errors by model and error type | Error rate < 2% |

**Labels:**
- `model`: Model name (e.g., `gemini-3-pro-preview`)
- `status`: Request outcome (`success` or `error`)
- `error_code`: Python exception type (e.g., `ResourceExhausted`, `DeadlineExceeded`)

### Job Metrics (General)

| Metric Name | Type | Description |
|-------------|------|-------------|
| `pegasus_job_status_events_total` | Counter | Job lifecycle events (queued, running, completed, failed) |
| `pegasus_job_failures_total` | Counter | Total failed jobs by type |
| `pegasus_job_latency_ms_avg` | Gauge | Average job execution time |
| `pegasus_job_latency_ms_max` | Gauge | Maximum job execution time |
| `pegasus_job_retries_total` | Counter | Job retry attempts |
| `pegasus_queue_depth` | Gauge | Current queue depth by status |

## Alert Policies

### 1. Success Rate Below 98% (CRITICAL)
- **Trigger**: Success rate drops below 98% for 5 minutes
- **Auto-close**: After 30 minutes
- **Escalation**: Page on-call if sustained >15 minutes
- **Runbook**: `docs/runbooks/gemini-failure-recovery.md`

### 2. P95 Latency Above 45s (WARNING)
- **Trigger**: p95 latency exceeds 45 seconds for 10 minutes
- **Auto-close**: After 30 minutes
- **Context**: Gemini 3 Pro uses extended reasoning, so variance is expected
- **Runbook**: `docs/runbooks/latency-investigation.md`

### 3. High Error Rate >2% (WARNING)
- **Trigger**: Error rate exceeds 2% for 10 minutes
- **Auto-close**: After 30 minutes
- **Common causes**: Quota exhaustion, malformed prompts, permission issues
- **Runbook**: `docs/runbooks/gemini-failure-recovery.md`

## Dashboard Widgets

The Gemini monitoring dashboard includes:

1. **Success Rate** - Line chart with 98% SLO threshold
2. **Latency Percentiles** - p50, p95, p99 with 45s target line
3. **Average Duration** - Scorecard with color-coded thresholds
4. **Maximum Duration** - Spike detection for outliers
5. **Total Requests** - Volume trend over time
6. **Error Breakdown** - Stacked area chart by error type
7. **Job Status Events** - Generation pipeline health
8. **Job Latency** - End-to-end generation time

## Viewing Metrics

### In Cloud Console
1. Navigate to [Monitoring > Metrics Explorer](https://console.cloud.google.com/monitoring/metrics-explorer)
2. Select resource type: `Prometheus Target`
3. Choose metric: `pegasus_thinking_duration_seconds_avg`
4. Add filters: `model = gemini-3-pro-preview`, `status = success`

### Using PromQL (Cloud Monitoring Query Language)
```promql
# Average reasoning time over last hour
avg_over_time(pegasus_thinking_duration_seconds_avg{model="gemini-3-pro-preview", status="success"}[1h])

# Success rate (5-minute rolling window)
rate(pegasus_thinking_requests_total{model="gemini-3-pro-preview", status="success"}[5m])
/ rate(pegasus_thinking_requests_total{model="gemini-3-pro-preview"}[5m])

# Error rate by error code
sum by (error_code) (rate(pegasus_thinking_errors_total{model="gemini-3-pro-preview"}[5m]))
```

### Via gcloud CLI
```bash
# Fetch current metric values
gcloud monitoring time-series list \
  --filter='metric.type="prometheus.googleapis.com/pegasus_thinking_duration_seconds_avg/gauge"' \
  --format=json

# Read alert policy status
gcloud alpha monitoring policies list --format=json
```

## Testing the Metrics Pipeline

### 1. Verify Metrics Export
```bash
# Check if metrics endpoint is accessible
curl https://pegasus-api-988514135894.us-central1.run.app/metrics

# Verify thinking metrics are present
curl -s https://pegasus-api-988514135894.us-central1.run.app/metrics | grep "pegasus_thinking"
```

### 2. Trigger Test Requests
```bash
# Upload and process a test lecture to generate metrics
./scripts/test-e2e-flow.sh
```

### 3. Verify Data in Cloud Monitoring
Wait 2-3 minutes for metrics to propagate, then:
```bash
gcloud monitoring time-series list \
  --filter='metric.type="prometheus.googleapis.com/pegasus_thinking_requests_total/counter"' \
  --format=json | jq '.[] | .points[0].value'
```

## Troubleshooting

### Metrics Not Appearing in Cloud Monitoring

**Symptom**: Dashboard shows "No data available"

**Causes**:
1. Cloud Run isn't exporting Prometheus metrics
2. Metrics endpoint (`/metrics`) not configured
3. Wrong metric prefix or label format

**Fix**:
```bash
# Check if metrics endpoint returns data
curl https://pegasus-api-988514135894.us-central1.run.app/metrics

# Verify Cloud Run is configured for Prometheus scraping
gcloud run services describe pegasus-api --region=us-central1 --format=json | jq '.spec.template.metadata.annotations'

# Expected: Should include prometheus.io/scrape and prometheus.io/port annotations
```

### Alerts Not Firing

**Symptom**: Alert conditions are met but no notifications

**Causes**:
1. Notification channels not configured
2. Alert policy disabled
3. Insufficient data points

**Fix**:
```bash
# List alert policies and check enabled status
gcloud alpha monitoring policies list --format=json | jq '.[] | {name: .displayName, enabled: .enabled}'

# Test notification channel
gcloud alpha monitoring channels list
gcloud alpha monitoring channels describe CHANNEL_ID
```

### High Latency False Positives

**Symptom**: Latency alerts firing despite normal operation

**Context**: Gemini 3 Pro reasoning time varies based on:
- Transcript length and complexity
- Model reasoning depth required
- Network conditions to global endpoint

**Fix**: Adjust threshold in `alerts.tf`:
```hcl
threshold_value = 60.0  # Increase from 45s to 60s if needed
```

## Next Steps

1. **Connect to Incident Management**: Integrate with PagerDuty or Opsgenie for on-call rotation
2. **Create SLO Dashboard**: Set up SLI/SLO tracking with error budget visualization
3. **Add Custom Metrics**: Track business metrics (artifacts generated, user satisfaction, etc.)
4. **Set Up Log-Based Metrics**: Create metrics from Cloud Logging patterns for deeper insights

## References

- [Google Cloud Monitoring Docs](https://cloud.google.com/monitoring/docs)
- [Prometheus Metrics Best Practices](https://prometheus.io/docs/practices/naming/)
- [Cloud Run Metrics](https://cloud.google.com/run/docs/monitoring)
- [Vertex AI SLA](https://cloud.google.com/vertex-ai/docs/reference/sla)
