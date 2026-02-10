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
REQUIRE_QUEUED_TRANSITION="${SMOKE_REQUIRE_QUEUED_TRANSITION:-1}"
ALLOW_QUEUE_FALLBACK="${SMOKE_ALLOW_QUEUE_FALLBACK:-0}"

cleanup() {
  rm -f "$AUDIO_FILE"
}
trap cleanup EXIT

echo "[1/5] Health check"
curl -fsS "$API_BASE_URL/health" >/tmp/pegasus_smoke_health.json
cat /tmp/pegasus_smoke_health.json

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

echo "[3/5] Ingest lecture: $LECTURE_ID"
curl -fsS -X POST "$API_BASE_URL/lectures/ingest" \
  -F "course_id=$COURSE_ID" \
  -F "lecture_id=$LECTURE_ID" \
  -F "preset_id=$PRESET_ID" \
  -F "title=Smoke Lecture" \
  -F "audio=@$AUDIO_FILE;type=audio/wav" >/tmp/pegasus_smoke_ingest.json
cat /tmp/pegasus_smoke_ingest.json

echo "[4/5] Enqueue transcription"
curl -fsS -X POST "$API_BASE_URL/lectures/$LECTURE_ID/transcribe?model=$MODEL" >/tmp/pegasus_smoke_enqueue.json
cat /tmp/pegasus_smoke_enqueue.json

JOB_ID="$(python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('/tmp/pegasus_smoke_enqueue.json').read_text())
print(payload.get('jobId', ''))
PY
)"

ENQUEUE_STATUS="$(python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('/tmp/pegasus_smoke_enqueue.json').read_text())
print(payload.get('status', ''))
PY
)"

if [[ -z "$JOB_ID" ]]; then
  echo "ERROR: Could not extract jobId from enqueue response" >&2
  exit 3
fi

seen_queued=0
seen_non_queued=0
if [[ "$ENQUEUE_STATUS" == "queued" ]]; then
  seen_queued=1
elif [[ -n "$ENQUEUE_STATUS" ]]; then
  seen_non_queued=1
fi

echo "[5/5] Polling job status for $JOB_ID (timeout: ${TIMEOUT_SEC}s)"
end=$((SECONDS + TIMEOUT_SEC))
last_status=""
while (( SECONDS < end )); do
  if ! curl -fsS "$API_BASE_URL/jobs/$JOB_ID" >/tmp/pegasus_smoke_job.json; then
    echo "WARN: failed to fetch job status; retrying..."
    sleep "$POLL_INTERVAL_SEC"
    continue
  fi

  status="$(python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('/tmp/pegasus_smoke_job.json').read_text())
print(payload.get('status', ''))
PY
)"

  if [[ "$status" == "queued" ]]; then
    seen_queued=1
  elif [[ -n "$status" ]]; then
    seen_non_queued=1
  fi

  if [[ "$status" != "$last_status" ]]; then
    echo "status=$status"
    cat /tmp/pegasus_smoke_job.json
    last_status="$status"
  fi

  if [[ "$status" == "succeeded" || "$status" == "failed" ]]; then
    terminal_queue_fallback="$(python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('/tmp/pegasus_smoke_job.json').read_text())
result = payload.get('result') if isinstance(payload, dict) else None
if isinstance(result, dict):
    value = result.get('queueFallback', '')
    print(value if isinstance(value, str) else '')
else:
    print('')
PY
)"

    if [[ "$REQUIRE_QUEUED_TRANSITION" == "1" || "$REQUIRE_QUEUED_TRANSITION" == "true" ]]; then
      if [[ "$seen_queued" != "1" || "$seen_non_queued" != "1" ]]; then
        echo "FAIL: did not observe queued -> non-queued transition for job $JOB_ID" >&2
        echo "      Set SMOKE_REQUIRE_QUEUED_TRANSITION=0 only for inline/non-queue environments." >&2
        exit 6
      fi
    fi

    if [[ "$ALLOW_QUEUE_FALLBACK" != "1" && "$ALLOW_QUEUE_FALLBACK" != "true" && -n "$terminal_queue_fallback" ]]; then
      echo "FAIL: job indicates queue fallback ('$terminal_queue_fallback'), so worker/queue wiring was not validated" >&2
      echo "      Set SMOKE_ALLOW_QUEUE_FALLBACK=1 only for non-worker environments." >&2
      exit 7
    fi

    if [[ "$status" == "succeeded" ]]; then
      echo "SUCCESS: queue + worker smoke test passed"
      exit 0
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
