#!/usr/bin/env bash
# teardown-gcp-monitoring.sh — Remove GCP Cloud Monitoring resources created
# by setup-gcp-monitoring.sh.
#
# Usage:
#   bash ops/monitoring/teardown-gcp-monitoring.sh
#
# Notification channels are preserved (they may be shared with other alerts).

set -euo pipefail

PROJECT="delta-student-486911-n5"

echo "==> Tearing down Pegasus monitoring resources in project $PROJECT"
echo ""

# -------------------------------------------------------------------------
# 1. Alert policies
# -------------------------------------------------------------------------
echo "--- [1/4] Alert policies ---"

for display_name in \
  "Pegasus API Down" \
  "Pegasus Failure Rate Spike (>10%)" \
  "Pegasus Generation Failure Burst"; do

  POLICY_ID=$(gcloud alpha monitoring policies list \
    --project="$PROJECT" \
    --filter="displayName=\"$display_name\"" \
    --format="value(name)" 2>/dev/null | head -1 || true)

  if [[ -n "$POLICY_ID" ]]; then
    gcloud alpha monitoring policies delete "$POLICY_ID" \
      --project="$PROJECT" --quiet 2>/dev/null
    echo "  Deleted alert: $display_name"
  else
    echo "  Alert not found: $display_name — skipping"
  fi
done

# -------------------------------------------------------------------------
# 2. Uptime check
# -------------------------------------------------------------------------
echo ""
echo "--- [2/4] Uptime check ---"

UPTIME_ID=$(gcloud monitoring uptime list-configs \
  --project="$PROJECT" \
  --filter="displayName=\"Pegasus API Health\"" \
  --format="value(name)" 2>/dev/null | head -1 || true)

if [[ -n "$UPTIME_ID" ]]; then
  gcloud monitoring uptime delete "$UPTIME_ID" \
    --project="$PROJECT" --quiet 2>/dev/null
  echo "  Deleted uptime check: Pegasus API Health"
else
  echo "  Uptime check not found — skipping"
fi

# -------------------------------------------------------------------------
# 3. Log-based metrics
# -------------------------------------------------------------------------
echo ""
echo "--- [3/4] Log-based metrics ---"

for metric_name in \
  "pegasus_job_failure_count" \
  "pegasus_job_completion_count" \
  "pegasus_generation_failure_count" \
  "pegasus_job_start_count"; do

  EXISTING=$(gcloud logging metrics describe "$metric_name" --project="$PROJECT" 2>/dev/null && echo "yes" || echo "no")
  if [[ "$EXISTING" == "yes" ]]; then
    gcloud logging metrics delete "$metric_name" \
      --project="$PROJECT" --quiet 2>/dev/null
    echo "  Deleted metric: $metric_name"
  else
    echo "  Metric not found: $metric_name — skipping"
  fi
done

# -------------------------------------------------------------------------
# 4. Dashboard
# -------------------------------------------------------------------------
echo ""
echo "--- [4/4] Dashboard ---"

DASH_ID=$(gcloud monitoring dashboards list \
  --project="$PROJECT" \
  --filter="displayName=\"Pegasus API — Pipeline & Infrastructure\"" \
  --format="value(name)" 2>/dev/null | head -1 || true)

if [[ -n "$DASH_ID" ]]; then
  gcloud monitoring dashboards delete "$DASH_ID" \
    --project="$PROJECT" --quiet 2>/dev/null
  echo "  Deleted dashboard: Pegasus API — Pipeline & Infrastructure"
else
  echo "  Dashboard not found — skipping"
fi

echo ""
echo "=== Teardown complete ==="
echo ""
echo "Note: Notification channels were preserved (may be shared)."
echo "To remove them manually: gcloud alpha monitoring channels list --project=$PROJECT"
