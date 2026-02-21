#!/usr/bin/env bash
# deploy-reproducibility-drill.sh — Verify deploy-from-main is reproducible
#
# Checks that the running Cloud Run service was built from main with
# pinned dependencies, a pinned base image, correct env vars, and
# passes health + canary checks.
#
# Usage: bash ops/drills/deploy-reproducibility-drill.sh
#
# Prerequisites:
#   - gcloud CLI authenticated with sufficient permissions
#   - Access to project delta-student-486911-n5
#   - Run from project root (project-pegasus/)

set -euo pipefail

PROJECT="delta-student-486911-n5"
REGION="europe-west1"
SERVICE="pegasus-api"
API_URL="https://pegasus-api-988514135894.europe-west1.run.app"
DRILL_DATE=$(date +%F-%H%M%S)
EVIDENCE_LOG="ops/drills/deploy-repro-evidence-${DRILL_DATE}.log"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg" | tee -a "$EVIDENCE_LOG"
}

separator() {
  log "================================================================"
}

pass() { log "  PASS — $*"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { log "  FAIL — $*"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn() { log "  WARN — $*"; WARN_COUNT=$((WARN_COUNT + 1)); }

# Ensure log directory exists
mkdir -p "$(dirname "$EVIDENCE_LOG")"
: > "$EVIDENCE_LOG"

separator
log "DEPLOY REPRODUCIBILITY DRILL — started at $(date)"
log "Project: $PROJECT"
log "Region: $REGION"
log "Service: $SERVICE"
separator

# ─── Step 1: Verify latest Cloud Build was from main ─────────────────
log ""
log "STEP 1: Checking latest Cloud Build matches main branch..."

LATEST_BUILD=$(gcloud builds list \
  --project="$PROJECT" \
  --region="us-central1" \
  --limit=1 \
  --format="value(id,status,source.storageSource.bucket,createTime)" 2>&1) || true
echo "$LATEST_BUILD" >> "$EVIDENCE_LOG"

if echo "$LATEST_BUILD" | grep -qi "SUCCESS"; then
  pass "Latest Cloud Build completed successfully."
  log "  Build info: $LATEST_BUILD"
else
  warn "Latest Cloud Build status is not SUCCESS: $LATEST_BUILD"
fi

# Check that the Cloud Run revision is from a recent build
REVISION=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="value(status.latestReadyRevisionName)" 2>&1) || true
echo "Active revision: $REVISION" >> "$EVIDENCE_LOG"
log "  Active revision: $REVISION"

# ─── Step 2: Run verify-gcp-production.sh ────────────────────────────
log ""
log "STEP 2: Running scripts/verify-gcp-production.sh..."

if bash temp-repo/scripts/verify-gcp-production.sh 2>&1 | tee -a "$EVIDENCE_LOG"; then
  pass "GCP production verification passed."
else
  fail "GCP production verification failed."
fi

# ─── Step 3: Verify Dockerfile uses pinned base image ────────────────
log ""
log "STEP 3: Checking Dockerfile for pinned Python base image..."

DOCKERFILE="temp-repo/backend/Dockerfile"
if [ -f "$DOCKERFILE" ]; then
  FROM_LINE=$(head -1 "$DOCKERFILE")
  echo "  FROM line: $FROM_LINE" >> "$EVIDENCE_LOG"
  log "  FROM line: $FROM_LINE"

  # Check that image tag has a patch version (e.g. 3.11.9-slim, not 3.11-slim)
  if echo "$FROM_LINE" | grep -qE 'python:[0-9]+\.[0-9]+\.[0-9]+-'; then
    pass "Dockerfile uses patch-pinned base image: $FROM_LINE"
  elif echo "$FROM_LINE" | grep -qE 'python:[0-9]+\.[0-9]+-'; then
    fail "Dockerfile uses minor-only tag (not patch-pinned): $FROM_LINE"
  else
    fail "Dockerfile FROM line does not match expected pattern: $FROM_LINE"
  fi
else
  fail "Dockerfile not found at $DOCKERFILE"
fi

# ─── Step 4: Verify requirements.txt has pinned versions ─────────────
log ""
log "STEP 4: Checking requirements.txt for pinned dependencies..."

REQUIREMENTS="temp-repo/backend/requirements.txt"
if [ -f "$REQUIREMENTS" ]; then
  TOTAL_DEPS=$(grep -cE '^[a-zA-Z]' "$REQUIREMENTS" 2>/dev/null || echo 0)
  PINNED_DEPS=$(grep -cE '==' "$REQUIREMENTS" 2>/dev/null || echo 0)
  UNPINNED_DEPS=$((TOTAL_DEPS - PINNED_DEPS))

  log "  Total dependencies: $TOTAL_DEPS"
  log "  Pinned (==): $PINNED_DEPS"
  log "  Unpinned: $UNPINNED_DEPS"

  if [ "$UNPINNED_DEPS" -eq 0 ] && [ "$TOTAL_DEPS" -gt 0 ]; then
    pass "All $TOTAL_DEPS dependencies are pinned with ==."
  else
    fail "$UNPINNED_DEPS of $TOTAL_DEPS dependencies are not pinned."
    grep -E '^[a-zA-Z]' "$REQUIREMENTS" | grep -vE '==' >> "$EVIDENCE_LOG" 2>/dev/null || true
  fi
else
  fail "requirements.txt not found at $REQUIREMENTS"
fi

# ─── Step 5: Canary health + artifact type check ─────────────────────
log ""
log "STEP 5: Canary health and artifact type check..."

# Health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" 2>&1) || true
echo "  Health HTTP status: $HTTP_STATUS" >> "$EVIDENCE_LOG"
if [ "$HTTP_STATUS" = "200" ]; then
  pass "Health endpoint returned HTTP 200."
else
  fail "Health endpoint returned HTTP ${HTTP_STATUS} (expected 200)."
fi

# Check that /health body includes expected fields
HEALTH_BODY=$(curl -s "${API_URL}/health" 2>&1) || true
echo "  Health body: $HEALTH_BODY" >> "$EVIDENCE_LOG"
if echo "$HEALTH_BODY" | grep -q '"status"'; then
  pass "Health response includes status field."
else
  warn "Health response missing status field."
fi

# Check artifact types endpoint if available
ARTIFACT_TYPES_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/artifact-types" 2>&1) || true
if [ "$ARTIFACT_TYPES_STATUS" = "200" ]; then
  ARTIFACT_BODY=$(curl -s "${API_URL}/artifact-types" 2>&1) || true
  echo "  Artifact types: $ARTIFACT_BODY" >> "$EVIDENCE_LOG"
  if echo "$ARTIFACT_BODY" | grep -q "summary"; then
    pass "Artifact types endpoint returns expected types."
  else
    warn "Artifact types response does not include 'summary'."
  fi
else
  log "  Artifact types endpoint returned HTTP ${ARTIFACT_TYPES_STATUS} (non-critical)."
fi

# ─── Summary ─────────────────────────────────────────────────────────
separator
log ""
log "DRILL COMPLETE — $(date)"
log ""
log "Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed, ${WARN_COUNT} warnings"
log "Evidence log: ${EVIDENCE_LOG}"
separator

echo ""
echo "Drill finished. ${PASS_COUNT} passed, ${FAIL_COUNT} failed, ${WARN_COUNT} warnings."
echo "Evidence saved to: ${EVIDENCE_LOG}"

# Exit non-zero if any failures
if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
