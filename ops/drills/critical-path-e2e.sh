#!/usr/bin/env bash
# critical-path-e2e.sh — Critical-path integration test drill for Pegasus
#
# Runs two test layers:
#   1. Unit integration tests (pytest, mocked dependencies)
#   2. Live E2E canary against deployed API (calls OpenAI, ~$0.01)
#
# All output is captured as evidence in a timestamped log file.
#
# Usage: bash ops/drills/critical-path-e2e.sh
#
# Prerequisites:
#   - Python 3.11+ with project dependencies installed
#   - For live E2E: API_BASE_URL set (defaults to production europe-west1)
#   - Optional: PLC_WRITE_API_TOKEN for write endpoints

set -uo pipefail

API_URL="${API_BASE_URL:-https://pegasus-api-988514135894.europe-west1.run.app}"
DRILL_DATE=$(date +%F-%H%M%S)
EVIDENCE_LOG="ops/drills/critical-path-evidence-${DRILL_DATE}.log"
REPO_ROOT="temp-repo"

PASS=0
FAIL=0

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg" | tee -a "$EVIDENCE_LOG"
}

separator() {
  log "================================================================"
}

record_result() {
  if [ "$1" -eq 0 ]; then
    PASS=$((PASS + 1))
    log "  RESULT: PASS"
  else
    FAIL=$((FAIL + 1))
    log "  RESULT: FAIL (exit code $1)"
  fi
}

# Ensure log directory exists
mkdir -p "$(dirname "$EVIDENCE_LOG")"
: > "$EVIDENCE_LOG"

separator
log "CRITICAL-PATH INTEGRATION TEST DRILL — started at $(date)"
log "Repo root: $REPO_ROOT"
log "API URL:   $API_URL"
separator

# ─── Step 1: Unit integration tests (pytest) ─────────────────────────
log ""
log "STEP 1: Running unit integration tests (pytest backend/tests/test_flow.py)..."
log ""

if (cd "$REPO_ROOT" && python3 -m pytest backend/tests/test_flow.py -v 2>&1) | tee -a "$EVIDENCE_LOG"; then
  STEP1_RC=0
else
  STEP1_RC=$?
fi
log ""
log "STEP 1: Unit integration tests"
record_result $STEP1_RC

# ─── Step 2: Live E2E canary ─────────────────────────────────────────
log ""
log "STEP 2: Running live E2E canary against $API_URL..."
log ""

if API_BASE_URL="$API_URL" python3 "$REPO_ROOT/scripts/canary_e2e_flow.py" 2>&1 | tee -a "$EVIDENCE_LOG"; then
  STEP2_RC=0
else
  STEP2_RC=$?
fi
log ""
log "STEP 2: Live E2E canary"
record_result $STEP2_RC

# ─── Summary ─────────────────────────────────────────────────────────
log ""
separator
log "DRILL COMPLETE — $(date)"
log "Results: $PASS passed, $FAIL failed (of 2 steps)"
log "Evidence log: ${EVIDENCE_LOG}"
separator

echo ""
echo "Drill finished. Evidence saved to: ${EVIDENCE_LOG}"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
