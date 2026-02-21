#!/usr/bin/env bash
# setup-gcp-monitoring.sh — Provision GCP Cloud Monitoring resources for Pegasus API.
#
# Usage:
#   bash ops/monitoring/setup-gcp-monitoring.sh YOUR_EMAIL@example.com
#
# Idempotent — safe to re-run. Creates resources only when they do not exist.

set -euo pipefail

PROJECT="delta-student-486911-n5"
SERVICE="pegasus-api"
REGION="europe-west1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NOTIFICATION_EMAIL="${1:-}"
if [[ -z "$NOTIFICATION_EMAIL" ]]; then
  echo "Usage: $0 <notification-email>"
  exit 1
fi

echo "==> Project: $PROJECT  Service: $SERVICE  Region: $REGION"
echo "==> Notification email: $NOTIFICATION_EMAIL"
echo ""

# -------------------------------------------------------------------------
# 1. Notification channel (email)
# -------------------------------------------------------------------------
echo "--- [1/5] Notification channel ---"

EXISTING_CHANNEL=$(gcloud alpha monitoring channels list \
  --project="$PROJECT" \
  --filter="type=\"email\" AND labels.email_address=\"$NOTIFICATION_EMAIL\"" \
  --format="value(name)" 2>/dev/null | head -1 || true)

if [[ -n "$EXISTING_CHANNEL" ]]; then
  echo "  Notification channel already exists: $EXISTING_CHANNEL"
  CHANNEL_ID="$EXISTING_CHANNEL"
else
  CHANNEL_ID=$(gcloud alpha monitoring channels create \
    --project="$PROJECT" \
    --display-name="Pegasus On-Call Email" \
    --type="email" \
    --channel-labels="email_address=$NOTIFICATION_EMAIL" \
    --format="value(name)" 2>/dev/null)
  echo "  Created notification channel: $CHANNEL_ID"
fi

# -------------------------------------------------------------------------
# 2. Log-based metrics
# -------------------------------------------------------------------------
echo ""
echo "--- [2/5] Log-based metrics ---"

create_log_metric_from_config() {
  local name="$1"
  local config_json="$2"

  if gcloud logging metrics describe "$name" --project="$PROJECT" > /dev/null 2>&1; then
    echo "  Metric $name already exists — skipping"
    return
  fi

  local tmpfile
  tmpfile=$(mktemp)
  echo "$config_json" > "$tmpfile"
  gcloud logging metrics create "$name" \
    --project="$PROJECT" \
    --config-from-file="$tmpfile"
  rm -f "$tmpfile"
  echo "  Created metric: $name"
}

create_log_metric_from_config "pegasus_job_failure_count" '{
  "description": "Count of failed Pegasus jobs by type",
  "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"pegasus-api\" AND jsonPayload.message=\"job.run.failed\"",
  "metricDescriptor": {
    "metricKind": "DELTA",
    "valueType": "INT64",
    "labels": [
      { "key": "job_type", "valueType": "STRING", "description": "Type of job (transcription, generation, export)" }
    ]
  },
  "labelExtractors": {
    "job_type": "EXTRACT(jsonPayload.job_type)"
  }
}'

create_log_metric_from_config "pegasus_job_completion_count" '{
  "description": "Count of completed Pegasus jobs by type",
  "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"pegasus-api\" AND jsonPayload.message=\"job.run.completed\"",
  "metricDescriptor": {
    "metricKind": "DELTA",
    "valueType": "INT64",
    "labels": [
      { "key": "job_type", "valueType": "STRING", "description": "Type of job (transcription, generation, export)" }
    ]
  },
  "labelExtractors": {
    "job_type": "EXTRACT(jsonPayload.job_type)"
  }
}'

create_log_metric_from_config "pegasus_generation_failure_count" '{
  "description": "Count of failed generation jobs",
  "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"pegasus-api\" AND jsonPayload.message=\"job.run.failed\" AND jsonPayload.job_type=\"generation\""
}'

create_log_metric_from_config "pegasus_job_start_count" '{
  "description": "Count of started Pegasus jobs by type",
  "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"pegasus-api\" AND jsonPayload.message=\"job.run.start\"",
  "metricDescriptor": {
    "metricKind": "DELTA",
    "valueType": "INT64",
    "labels": [
      { "key": "job_type", "valueType": "STRING", "description": "Type of job (transcription, generation, export)" }
    ]
  },
  "labelExtractors": {
    "job_type": "EXTRACT(jsonPayload.job_type)"
  }
}'

# -------------------------------------------------------------------------
# 3. Uptime check on /health
# -------------------------------------------------------------------------
echo ""
echo "--- [3/5] Uptime check ---"

UPTIME_DISPLAY="Pegasus API Health"
SERVICE_HOST="${SERVICE}-988514135894.${REGION}.run.app"
EXISTING_UPTIME=$(gcloud monitoring uptime list-configs \
  --project="$PROJECT" \
  --filter="displayName=\"$UPTIME_DISPLAY\"" \
  --format="value(name)" 2>/dev/null | head -1 || true)

if [[ -n "$EXISTING_UPTIME" ]]; then
  echo "  Uptime check already exists: $EXISTING_UPTIME"
  UPTIME_ID="$EXISTING_UPTIME"
else
  UPTIME_ID=$(gcloud monitoring uptime create "$UPTIME_DISPLAY" \
    --project="$PROJECT" \
    --resource-type="uptime-url" \
    --resource-labels="host=$SERVICE_HOST,project_id=$PROJECT" \
    --path="/health" \
    --protocol="https" \
    --period="5" \
    --regions="usa-iowa,europe,asia-pacific" \
    --format="value(name)")
  echo "  Created uptime check: $UPTIME_ID"
fi

# -------------------------------------------------------------------------
# 4. Alert policies
# -------------------------------------------------------------------------
echo ""
echo "--- [4/5] Alert policies ---"

create_alert_if_missing() {
  local display_name="$1"
  local policy_json="$2"

  EXISTING_ALERT=$(gcloud alpha monitoring policies list \
    --project="$PROJECT" \
    --filter="displayName=\"$display_name\"" \
    --format="value(name)" 2>/dev/null | head -1 || true)

  if [[ -n "$EXISTING_ALERT" ]]; then
    echo "  Alert '$display_name' already exists — skipping"
    return
  fi

  local tmpfile
  tmpfile=$(mktemp)
  echo "$policy_json" > "$tmpfile"
  gcloud alpha monitoring policies create \
    --project="$PROJECT" \
    --policy-from-file="$tmpfile" 2>/dev/null
  rm -f "$tmpfile"
  echo "  Created alert: $display_name"
}

# 4a. API Down — Uptime check failure
# Extract the short uptime check ID from the full resource name
UPTIME_SHORT_ID=$(echo "$UPTIME_ID" | grep -oE '[^/]+$')

create_alert_if_missing "Pegasus API Down" "$(cat <<ALERT_JSON
{
  "displayName": "Pegasus API Down",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Uptime check failing",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND metric.labels.check_id=\"$UPTIME_SHORT_ID\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 1,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "300s",
            "perSeriesAligner": "ALIGN_NEXT_OLDER",
            "crossSeriesReducer": "REDUCE_COUNT_FALSE"
          }
        ]
      }
    }
  ],
  "notificationChannels": ["$CHANNEL_ID"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
ALERT_JSON
)"

# 4b. Failure Rate Spike (>10%) — fires when failure count rate exceeds threshold
create_alert_if_missing "Pegasus Failure Rate Spike (>10%)" "$(cat <<ALERT_JSON
{
  "displayName": "Pegasus Failure Rate Spike (>10%)",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Job failure rate elevated",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/pegasus_job_failure_count\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0.10,
        "duration": "600s",
        "aggregations": [
          {
            "alignmentPeriod": "600s",
            "perSeriesAligner": "ALIGN_RATE",
            "crossSeriesReducer": "REDUCE_SUM"
          }
        ]
      }
    }
  ],
  "notificationChannels": ["$CHANNEL_ID"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
ALERT_JSON
)"

# 4c. Generation Failure Burst (≥5 in 10 min)
create_alert_if_missing "Pegasus Generation Failure Burst" "$(cat <<ALERT_JSON
{
  "displayName": "Pegasus Generation Failure Burst",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Generation failures >= 5 in 10m",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/pegasus_generation_failure_count\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 4,
        "duration": "600s",
        "aggregations": [
          {
            "alignmentPeriod": "600s",
            "perSeriesAligner": "ALIGN_SUM",
            "crossSeriesReducer": "REDUCE_SUM"
          }
        ]
      }
    }
  ],
  "notificationChannels": ["$CHANNEL_ID"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
ALERT_JSON
)"

# -------------------------------------------------------------------------
# 5. Dashboard
# -------------------------------------------------------------------------
echo ""
echo "--- [5/5] Dashboard ---"

DASHBOARD_DISPLAY="Pegasus API — Pipeline & Infrastructure"
EXISTING_DASH=$(gcloud monitoring dashboards list \
  --project="$PROJECT" \
  --filter="displayName=\"$DASHBOARD_DISPLAY\"" \
  --format="value(name)" 2>/dev/null | head -1 || true)

if [[ -n "$EXISTING_DASH" ]]; then
  echo "  Dashboard already exists: $EXISTING_DASH"
else
  gcloud monitoring dashboards create \
    --project="$PROJECT" \
    --config-from-file="$SCRIPT_DIR/gcp-dashboard.json" 2>/dev/null
  echo "  Created dashboard: $DASHBOARD_DISPLAY"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Verify in GCP Console:"
echo "  Dashboards:  https://console.cloud.google.com/monitoring/dashboards?project=$PROJECT"
echo "  Alerts:      https://console.cloud.google.com/monitoring/alerting?project=$PROJECT"
echo "  Uptime:      https://console.cloud.google.com/monitoring/uptime?project=$PROJECT"
echo "  Log metrics: https://console.cloud.google.com/logs/metrics?project=$PROJECT"
