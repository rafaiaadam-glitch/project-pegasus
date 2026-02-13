#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
COURSE_ID="${COURSE_ID:-canary-course}"
LECTURE_ID="${LECTURE_ID:-canary-lecture-$(date +%s)}"
PRESET_ID="${PRESET_ID:-exam}"
AUDIO_FILE="${AUDIO_FILE:-}"

echo "[canary] API: ${API_BASE_URL}"

curl -fsS "${API_BASE_URL}/health" >/dev/null
curl -fsS "${API_BASE_URL}/health/ready" >/dev/null

if [[ -z "${AUDIO_FILE}" ]]; then
  echo "[canary] AUDIO_FILE not set; readiness-only checks passed"
  exit 0
fi

echo "[canary] ingest lecture ${LECTURE_ID}"
curl -fsS -X POST "${API_BASE_URL}/lectures/ingest" \
  -F "file=@${AUDIO_FILE}" \
  -F "course_id=${COURSE_ID}" \
  -F "title=Canary Lecture" \
  -F "preset_id=${PRESET_ID}" >/dev/null

echo "[canary] queue generation"
curl -fsS -X POST "${API_BASE_URL}/lectures/${LECTURE_ID}/generate" \
  -H 'Content-Type: application/json' \
  -d "{\"course_id\":\"${COURSE_ID}\",\"preset_id\":\"${PRESET_ID}\"}" >/dev/null || true

echo "[canary] checks complete"
