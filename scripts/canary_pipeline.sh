#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "ERROR: API_BASE_URL is required (e.g. https://pegasus-api.example.com)" >&2
  exit 2
fi

COURSE_ID="${CANARY_COURSE_ID:-canary-course}"
LECTURE_ID="${CANARY_LECTURE_ID:-canary-lecture-$(date +%s)}"
PRESET_ID="${CANARY_PRESET_ID:-exam-mode}"
TRANSCRIBE_PROVIDER="${CANARY_TRANSCRIBE_PROVIDER:-}"
TRANSCRIBE_LANGUAGE="${CANARY_TRANSCRIBE_LANGUAGE:-}"
EXPORT_TYPE="${CANARY_EXPORT_TYPE:-markdown}"
TIMEOUT_SEC="${CANARY_TIMEOUT_SEC:-900}"
POLL_INTERVAL_SEC="${CANARY_POLL_INTERVAL_SEC:-5}"
AUDIO_FILE="${CANARY_AUDIO_FILE:-canary.wav}"
WRITE_API_TOKEN="${PLC_WRITE_API_TOKEN:-${CANARY_WRITE_API_TOKEN:-}}"
WEBHOOK_URL="${CANARY_RESULT_WEBHOOK_URL:-}"
SUMMARY_FILE="${CANARY_SUMMARY_FILE:-}"
CLEANUP_LECTURE="${CANARY_CLEANUP_LECTURE:-0}"

RUN_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_START_EPOCH="$(date +%s)"

CURL_HEADERS=()
if [[ -n "$WRITE_API_TOKEN" ]]; then
  CURL_HEADERS+=("-H" "Authorization: Bearer $WRITE_API_TOKEN")
fi

transcribe_job_id=""
generate_job_id=""
export_job_id=""
health_seconds=0
ingest_seconds=0
transcribe_seconds=0
generate_seconds=0
export_seconds=0
export_fetch_seconds=0
cleanup_seconds=0
run_status="failed"
failure_stage=""
failure_message=""
cleanup_done=0

now_epoch() {
  date +%s
}

bool_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

perform_cleanup() {
  if [[ "$cleanup_done" == "1" ]]; then
    return 0
  fi
  cleanup_done=1

  rm -f "$AUDIO_FILE"

  if bool_true "$CLEANUP_LECTURE"; then
    local start
    start="$(now_epoch)"
    local delete_url="$API_BASE_URL/lectures/$LECTURE_ID?purge_storage=true"
    if ! curl -fsS -X DELETE "$delete_url" "${CURL_HEADERS[@]}" >/tmp/pegasus_canary_cleanup.json; then
      echo "WARN: failed lecture cleanup for $LECTURE_ID" >&2
    fi
    cleanup_seconds=$(( $(now_epoch) - start ))
  fi
}
trap perform_cleanup EXIT

emit_summary() {
  local ended_at
  ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local run_duration
  run_duration=$(( $(now_epoch) - RUN_START_EPOCH ))

  local summary_json
  summary_json="$(env \
    RUN_STATUS="$run_status" \
    RUN_STARTED_AT="$RUN_STARTED_AT" \
    RUN_ENDED_AT="$ended_at" \
    RUN_DURATION="$run_duration" \
    API_BASE_URL="$API_BASE_URL" \
    COURSE_ID="$COURSE_ID" \
    LECTURE_ID="$LECTURE_ID" \
    PRESET_ID="$PRESET_ID" \
    JOB_TRANSCRIBE="$transcribe_job_id" \
    JOB_GENERATE="$generate_job_id" \
    JOB_EXPORT="$export_job_id" \
    T_HEALTH="$health_seconds" \
    T_INGEST="$ingest_seconds" \
    T_TRANSCRIBE="$transcribe_seconds" \
    T_GENERATE="$generate_seconds" \
    T_EXPORT="$export_seconds" \
    T_EXPORT_FETCH="$export_fetch_seconds" \
    T_CLEANUP="$cleanup_seconds" \
    FAILURE_STAGE="$failure_stage" \
    FAILURE_MESSAGE="$failure_message" \
    python - <<'PY'
import json
import os

payload = {
    "status": os.environ["RUN_STATUS"],
    "startedAt": os.environ["RUN_STARTED_AT"],
    "endedAt": os.environ["RUN_ENDED_AT"],
    "durationSec": int(os.environ["RUN_DURATION"]),
    "apiBaseUrl": os.environ["API_BASE_URL"],
    "courseId": os.environ["COURSE_ID"],
    "lectureId": os.environ["LECTURE_ID"],
    "presetId": os.environ["PRESET_ID"],
    "jobs": {
        "transcribe": os.environ["JOB_TRANSCRIBE"],
        "generate": os.environ["JOB_GENERATE"],
        "export": os.environ["JOB_EXPORT"],
    },
    "timingsSec": {
        "health": int(os.environ["T_HEALTH"]),
        "ingest": int(os.environ["T_INGEST"]),
        "transcribe": int(os.environ["T_TRANSCRIBE"]),
        "generate": int(os.environ["T_GENERATE"]),
        "export": int(os.environ["T_EXPORT"]),
        "exportFetch": int(os.environ["T_EXPORT_FETCH"]),
        "cleanup": int(os.environ["T_CLEANUP"]),
    },
    "failure": {
        "stage": os.environ["FAILURE_STAGE"],
        "message": os.environ["FAILURE_MESSAGE"],
    },
}
print(json.dumps(payload))
PY
)"

  if [[ -n "$SUMMARY_FILE" ]]; then
    printf '%s\n' "$summary_json" > "$SUMMARY_FILE"
    echo "Summary written to $SUMMARY_FILE"
  fi

  echo "CANARY_SUMMARY $summary_json"

  if [[ -n "$WEBHOOK_URL" ]]; then
    curl -fsS -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "$summary_json" >/tmp/pegasus_canary_webhook.json || {
      echo "WARN: failed to deliver webhook payload to $WEBHOOK_URL" >&2
      return 1
    }
    echo "Webhook delivered to $WEBHOOK_URL"
  fi
}

fail() {
  failure_stage="$1"
  failure_message="$2"
  run_status="failed"
  echo "ERROR[$failure_stage]: $failure_message" >&2
  perform_cleanup
  emit_summary || true
  exit 1
}

poll_job_until_terminal() {
  local job_id="$1"
  local label="$2"
  local out_file="$3"
  local end=$((SECONDS + TIMEOUT_SEC))
  local last_status=""

  while (( SECONDS < end )); do
    if ! curl -fsS "$API_BASE_URL/jobs/$job_id" >"$out_file"; then
      sleep "$POLL_INTERVAL_SEC"
      continue
    fi

    local status
    status="$(python - <<PY
import json
from pathlib import Path
payload = json.loads(Path('$out_file').read_text())
print(payload.get('status', ''))
PY
)"

    if [[ "$status" != "$last_status" ]]; then
      echo "[$label] status=$status"
      cat "$out_file"
      last_status="$status"
    fi

    if [[ "$status" == "succeeded" ]]; then
      return 0
    fi

    if [[ "$status" == "failed" ]]; then
      return 1
    fi

    sleep "$POLL_INTERVAL_SEC"
  done

  return 2
}

step_start="$(now_epoch)"
echo "[1/8] Health check"
curl -fsS "$API_BASE_URL/health" >/tmp/pegasus_canary_health.json || fail "health" "health endpoint failed"
cat /tmp/pegasus_canary_health.json
health_seconds=$(( $(now_epoch) - step_start ))

step_start="$(now_epoch)"
echo "[2/8] Create test audio"
python - <<PY
from pathlib import Path
import wave

path = Path("$AUDIO_FILE")
with wave.open(str(path), 'w') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(16000)
    wav.writeframes(b'\x00\x00' * 32000)
print(path)
PY

echo "[3/8] Ingest lecture: $LECTURE_ID"
curl -fsS -X POST "$API_BASE_URL/lectures/ingest" \
  "${CURL_HEADERS[@]}" \
  -F "course_id=$COURSE_ID" \
  -F "lecture_id=$LECTURE_ID" \
  -F "preset_id=$PRESET_ID" \
  -F "title=Synthetic Canary Lecture" \
  -F "audio=@$AUDIO_FILE;type=audio/wav" >/tmp/pegasus_canary_ingest.json || fail "ingest" "lecture ingest failed"
cat /tmp/pegasus_canary_ingest.json
ingest_seconds=$(( $(now_epoch) - step_start ))

step_start="$(now_epoch)"
echo "[4/8] Enqueue transcription"
transcribe_query=""
if [[ -n "$TRANSCRIBE_PROVIDER" ]]; then
  transcribe_query="provider=$TRANSCRIBE_PROVIDER"
fi
if [[ -n "$TRANSCRIBE_LANGUAGE" ]]; then
  if [[ -n "$transcribe_query" ]]; then
    transcribe_query+="&"
  fi
  transcribe_query+="language_code=$TRANSCRIBE_LANGUAGE"
fi
transcribe_url="$API_BASE_URL/lectures/$LECTURE_ID/transcribe"
if [[ -n "$transcribe_query" ]]; then
  transcribe_url+="?$transcribe_query"
fi

curl -fsS -X POST "$transcribe_url" "${CURL_HEADERS[@]}" >/tmp/pegasus_canary_transcribe_enqueue.json || fail "transcribe_enqueue" "transcription enqueue failed"
cat /tmp/pegasus_canary_transcribe_enqueue.json

transcribe_job_id="$(python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('/tmp/pegasus_canary_transcribe_enqueue.json').read_text())
print(payload.get('jobId', ''))
PY
)"

if [[ -z "$transcribe_job_id" ]]; then
  fail "transcribe_enqueue" "missing transcription jobId"
fi

if ! poll_job_until_terminal "$transcribe_job_id" "transcription" "/tmp/pegasus_canary_transcribe_job.json"; then
  rc=$?
  if [[ $rc -eq 2 ]]; then
    fail "transcribe_poll" "transcription job timed out"
  fi
  fail "transcribe_poll" "transcription job failed"
fi
transcribe_seconds=$(( $(now_epoch) - step_start ))

step_start="$(now_epoch)"
echo "[5/8] Enqueue generation"
curl -fsS -X POST "$API_BASE_URL/lectures/$LECTURE_ID/generate" \
  "${CURL_HEADERS[@]}" \
  -H 'Content-Type: application/json' \
  -d "{\"course_id\":\"$COURSE_ID\",\"preset_id\":\"$PRESET_ID\"}" >/tmp/pegasus_canary_generate_enqueue.json || fail "generate_enqueue" "generation enqueue failed"
cat /tmp/pegasus_canary_generate_enqueue.json

generate_job_id="$(python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('/tmp/pegasus_canary_generate_enqueue.json').read_text())
print(payload.get('jobId', ''))
PY
)"

if [[ -z "$generate_job_id" ]]; then
  fail "generate_enqueue" "missing generation jobId"
fi

if ! poll_job_until_terminal "$generate_job_id" "generation" "/tmp/pegasus_canary_generate_job.json"; then
  rc=$?
  if [[ $rc -eq 2 ]]; then
    fail "generate_poll" "generation job timed out"
  fi
  fail "generate_poll" "generation job failed"
fi
generate_seconds=$(( $(now_epoch) - step_start ))

step_start="$(now_epoch)"
echo "[6/8] Enqueue export"
curl -fsS -X POST "$API_BASE_URL/lectures/$LECTURE_ID/export" \
  "${CURL_HEADERS[@]}" >/tmp/pegasus_canary_export_enqueue.json || fail "export_enqueue" "export enqueue failed"
cat /tmp/pegasus_canary_export_enqueue.json

export_job_id="$(python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('/tmp/pegasus_canary_export_enqueue.json').read_text())
print(payload.get('jobId', ''))
PY
)"

if [[ -z "$export_job_id" ]]; then
  fail "export_enqueue" "missing export jobId"
fi

if ! poll_job_until_terminal "$export_job_id" "export" "/tmp/pegasus_canary_export_job.json"; then
  rc=$?
  if [[ $rc -eq 2 ]]; then
    fail "export_poll" "export job timed out"
  fi
  fail "export_poll" "export job failed"
fi
export_seconds=$(( $(now_epoch) - step_start ))

step_start="$(now_epoch)"
echo "[7/8] Verify export artifact availability: $EXPORT_TYPE"
curl -fsS "$API_BASE_URL/exports/$LECTURE_ID/$EXPORT_TYPE" >/tmp/pegasus_canary_export_fetch.json || fail "export_fetch" "export artifact fetch failed"
cat /tmp/pegasus_canary_export_fetch.json
export_fetch_seconds=$(( $(now_epoch) - step_start ))

echo "[8/8] Canary PASSED lecture_id=$LECTURE_ID"
run_status="passed"
perform_cleanup
emit_summary
