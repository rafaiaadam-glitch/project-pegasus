#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "ERROR: API_BASE_URL is required (e.g. https://pegasus-api.example.com)" >&2
  exit 2
fi

COURSE_ID="${SMOKE_COURSE_ID:-smoke-course}"
LECTURE_ID="${SMOKE_LECTURE_ID:-smoke-lecture-$(date +%s)}"
PRESET_ID="${SMOKE_PRESET_ID:-exam}"
MODEL="${SMOKE_MODEL:-base}"
TIMEOUT_SEC="${SMOKE_TIMEOUT_SEC:-300}"
POLL_INTERVAL_SEC="${SMOKE_POLL_INTERVAL_SEC:-5}"
AUDIO_FILE="${SMOKE_AUDIO_FILE:-smoke.wav}"
ACCEPT_FAILED_TERMINAL="${SMOKE_ACCEPT_FAILED_TERMINAL:-1}"
REQUIRE_QUEUE_PATH="${SMOKE_REQUIRE_QUEUE_PATH:-1}"
REQUIRE_RUNNING_STATE="${SMOKE_REQUIRE_RUNNING_STATE:-0}"

TMP_DIR="$(mktemp -d -t pegasus-smoke-XXXXXX)"
GENERATED_AUDIO="0"

cleanup() {
  if [[ "$GENERATED_AUDIO" == "1" ]]; then
    rm -f "$AUDIO_FILE"
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

health_json="$TMP_DIR/health.json"
ingest_json="$TMP_DIR/ingest.json"
enqueue_json="$TMP_DIR/enqueue.json"
job_json="$TMP_DIR/job.json"

echo "[1/5] Health check"
curl -fsS "$API_BASE_URL/health" >"$health_json"
cat "$health_json"

if [[ -f "$AUDIO_FILE" ]]; then
  echo "[2/5] Using existing audio file: $AUDIO_FILE"
else
  echo "[2/5] Create placeholder WAV: $AUDIO_FILE"
  python - <<PY
from pathlib import Path
import wave

path = Path("$AUDIO_FILE")
with wave.open(str(path), 'w') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(16000)
    wav.writeframes(b'\x00\x00' * 16000)
print(path)
PY
  GENERATED_AUDIO="1"
fi

echo "[3/5] Ingest lecture: $LECTURE_ID"
curl -fsS -X POST "$API_BASE_URL/lectures/ingest" \
  -F "course_id=$COURSE_ID" \
  -F "lecture_id=$LECTURE_ID" \
  -F "preset_id=$PRESET_ID" \
  -F "title=Smoke Lecture" \
  -F "audio=@$AUDIO_FILE;type=audio/wav" >"$ingest_json"
cat "$ingest_json"

echo "[4/5] Enqueue transcription"
curl -fsS -X POST "$API_BASE_URL/lectures/$LECTURE_ID/transcribe?model=$MODEL" >"$enqueue_json"
cat "$enqueue_json"

JOB_ID="$(python - <<PY
import json
from pathlib import Path
payload=json.loads(Path('$enqueue_json').read_text())
print(payload.get('jobId',''))
PY
)"

if [[ -z "$JOB_ID" ]]; then
  echo "ERROR: Could not extract jobId from enqueue response" >&2
  exit 3
fi

echo "[5/5] Polling job status for $JOB_ID (timeout: ${TIMEOUT_SEC}s)"
end=$((SECONDS + TIMEOUT_SEC))
last_status=""
saw_running="0"
while (( SECONDS < end )); do
  if ! curl -fsS "$API_BASE_URL/jobs/$JOB_ID" >"$job_json"; then
    echo "WARN: failed to fetch job status; retrying..."
    sleep "$POLL_INTERVAL_SEC"
    continue
  fi

  status="$(python - <<PY
import json
from pathlib import Path
payload=json.loads(Path('$job_json').read_text())
print(payload.get('status',''))
PY
)"

  if [[ "$status" != "$last_status" ]]; then
    echo "status=$status"
    cat "$job_json"
    last_status="$status"
  fi

  if [[ "$status" == "running" ]]; then
    saw_running="1"
  fi

  queue_fallback="$(python - <<PY
import json
from pathlib import Path
payload=json.loads(Path('$job_json').read_text())
result=payload.get('result') or {}
print(result.get('queueFallback','') if isinstance(result, dict) else '')
PY
)"

  if [[ "$REQUIRE_QUEUE_PATH" == "1" || "$REQUIRE_QUEUE_PATH" == "true" ]]; then
    if [[ "$queue_fallback" == "inline" ]]; then
      echo "FAIL: job used inline queue fallback instead of Redis worker path" >&2
      exit 6
    fi
  fi

  if [[ "$status" == "succeeded" ]]; then
    if [[ "$REQUIRE_RUNNING_STATE" == "1" || "$REQUIRE_RUNNING_STATE" == "true" ]]; then
      if [[ "$saw_running" != "1" ]]; then
        echo "FAIL: job never reached running state; enable finer polling or disable SMOKE_REQUIRE_RUNNING_STATE" >&2
        exit 7
      fi
    fi
    echo "SUCCESS: queue + worker smoke test passed"
    exit 0
  fi

  if [[ "$status" == "failed" ]]; then
    if [[ "$REQUIRE_RUNNING_STATE" == "1" || "$REQUIRE_RUNNING_STATE" == "true" ]]; then
      if [[ "$saw_running" != "1" ]]; then
        echo "FAIL: job failed without observing running state; enable finer polling or disable SMOKE_REQUIRE_RUNNING_STATE" >&2
        exit 8
      fi
    fi
    if [[ "$ACCEPT_FAILED_TERMINAL" == "1" || "$ACCEPT_FAILED_TERMINAL" == "true" ]]; then
      echo "SUCCESS: job failed terminally, but queue + worker path executed (set SMOKE_ACCEPT_FAILED_TERMINAL=0 to treat this as failure)"
      exit 0
    fi
    echo "FAIL: job reached failed terminal state (queue + worker path executed)" >&2
    exit 4
  fi

  sleep "$POLL_INTERVAL_SEC"
done

echo "TIMEOUT: job did not reach terminal state within ${TIMEOUT_SEC}s" >&2
exit 5
