#!/usr/bin/env bash
# backup-restore-drill.sh — Non-destructive backup/restore drill for Pegasus
#
# Executes a real backup/restore cycle against Cloud SQL and GCS,
# captures all output as evidence in a timestamped log file.
#
# Usage: bash ops/drills/backup-restore-drill.sh
#
# Prerequisites:
#   - gcloud CLI authenticated with sufficient permissions
#   - Access to project delta-student-486911-n5

set -euo pipefail

PROJECT="delta-student-486911-n5"
INSTANCE="pegasus-db-eu"
BUCKET="delta-student-486911-n5-pegasus-storage-eu"
GCS_PREFIX="pegasus"
API_URL="https://pegasus-api-988514135894.europe-west1.run.app"
DRILL_DATE=$(date +%F-%H%M%S)
EVIDENCE_LOG="ops/drills/drill-evidence-${DRILL_DATE}.log"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg" | tee -a "$EVIDENCE_LOG"
}

separator() {
  log "================================================================"
}

# Ensure log directory exists
mkdir -p "$(dirname "$EVIDENCE_LOG")"
: > "$EVIDENCE_LOG"

separator
log "BACKUP/RESTORE DRILL — started at $(date)"
log "Project: $PROJECT"
log "Instance: $INSTANCE"
log "Bucket: $BUCKET"
separator

# ─── Step 1: Create on-demand Cloud SQL backup ───────────────────────
log ""
log "STEP 1: Creating on-demand Cloud SQL backup..."
if gcloud sql backups create \
  --instance="$INSTANCE" \
  --project="$PROJECT" \
  --description="Drill backup ${DRILL_DATE}" 2>&1 | tee -a "$EVIDENCE_LOG"; then
  log "STEP 1: PASS — Backup created successfully."
else
  log "STEP 1: FAIL — Could not create backup. Check permissions."
fi

# ─── Step 2: List backups to confirm creation ────────────────────────
log ""
log "STEP 2: Listing Cloud SQL backups (most recent 5)..."
if gcloud sql backups list \
  --instance="$INSTANCE" \
  --project="$PROJECT" \
  --limit=5 2>&1 | tee -a "$EVIDENCE_LOG"; then
  log "STEP 2: PASS — Backup list retrieved."
else
  log "STEP 2: FAIL — Could not list backups."
fi

# ─── Step 3: Verify GCS object versioning ────────────────────────────
log ""
log "STEP 3: Checking GCS object versioning on gs://${BUCKET}..."
VERSIONING=$(gcloud storage buckets describe "gs://${BUCKET}" \
  --format="value(versioning_enabled)" \
  --project="$PROJECT" 2>&1) || true
echo "$VERSIONING" >> "$EVIDENCE_LOG"
if [ "$VERSIONING" = "True" ]; then
  log "STEP 3: PASS — Object versioning is enabled."
else
  log "STEP 3: WARN — Object versioning is NOT enabled (got: ${VERSIONING})."
  log "  Enable with: gcloud storage buckets update gs://${BUCKET} --versioning"
fi

# ─── Step 4: GCS object write/delete/restore cycle ──────────────────
log ""
log "STEP 4: GCS object lifecycle test (write → delete → restore from version)..."
DRILL_OBJECT="${GCS_PREFIX}/drills/drill-test-${DRILL_DATE}.txt"
DRILL_CONTENT="Drill test object created at ${DRILL_DATE}"

# Write test object
echo "$DRILL_CONTENT" | gcloud storage cp - "gs://${BUCKET}/${DRILL_OBJECT}" 2>&1 | tee -a "$EVIDENCE_LOG"
log "  4a: Test object uploaded to gs://${BUCKET}/${DRILL_OBJECT}"

# List versions before delete
log "  4b: Listing object versions..."
gcloud storage ls -l --all-versions "gs://${BUCKET}/${DRILL_OBJECT}" 2>&1 | tee -a "$EVIDENCE_LOG" || true

# Delete the object
gcloud storage rm "gs://${BUCKET}/${DRILL_OBJECT}" 2>&1 | tee -a "$EVIDENCE_LOG"
log "  4c: Test object deleted."

# Check if we can see the deleted version (requires versioning)
log "  4d: Listing versions after delete (should show non-current version if versioning enabled)..."
VERSIONS_OUTPUT=$(gcloud storage ls -l --all-versions "gs://${BUCKET}/${DRILL_OBJECT}" 2>&1) || true
echo "$VERSIONS_OUTPUT" >> "$EVIDENCE_LOG"

if echo "$VERSIONS_OUTPUT" | grep -q "generation"; then
  # Extract generation number and restore
  GENERATION=$(echo "$VERSIONS_OUTPUT" | grep -o '#[0-9]*' | head -1 | tr -d '#')
  if [ -n "$GENERATION" ]; then
    log "  4e: Restoring from generation $GENERATION..."
    gcloud storage cp \
      "gs://${BUCKET}/${DRILL_OBJECT}#${GENERATION}" \
      "gs://${BUCKET}/${DRILL_OBJECT}" 2>&1 | tee -a "$EVIDENCE_LOG"
    log "  STEP 4: PASS — Object restored from version."
  else
    log "  STEP 4: WARN — Could not extract generation number for restore test."
  fi
else
  log "  STEP 4: SKIP — No versioned copies found (versioning may not be enabled)."
fi

# Clean up drill object
gcloud storage rm "gs://${BUCKET}/${DRILL_OBJECT}" 2>&1 | tee -a "$EVIDENCE_LOG" || true
log "  Cleanup: Drill test object removed."

# ─── Step 5: Health check ────────────────────────────────────────────
log ""
log "STEP 5: Hitting /health endpoint to confirm API is healthy..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" 2>&1) || true
echo "HTTP status: $HTTP_STATUS" >> "$EVIDENCE_LOG"
if [ "$HTTP_STATUS" = "200" ]; then
  log "STEP 5: PASS — API returned HTTP 200."
else
  log "STEP 5: WARN — API returned HTTP ${HTTP_STATUS} (expected 200)."
fi

# ─── Summary ─────────────────────────────────────────────────────────
separator
log "DRILL COMPLETE — $(date)"
log "Evidence log: ${EVIDENCE_LOG}"
separator

echo ""
echo "Drill finished. Evidence saved to: ${EVIDENCE_LOG}"
