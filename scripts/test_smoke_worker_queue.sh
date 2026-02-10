#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT_DIR/scripts/smoke_worker_queue.sh"

run_case() {
  local name="$1"
  local scenario="$2"
  local expect_code="$3"
  local allow_fallback="${4:-0}"
  local require_transition="${5:-1}"

  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN

  mkdir -p "$tmp/bin"
  cat > "$tmp/bin/curl" <<'CURL'
#!/usr/bin/env bash
set -euo pipefail

url=""
for arg in "$@"; do
  if [[ "$arg" == http://* || "$arg" == https://* ]]; then
    url="$arg"
  fi
done
if [[ -z "$url" ]]; then
  echo "no url argument found" >&2
  exit 8
fi
state_file="${SMOKE_FAKE_STATE_FILE:?missing state file}"
scenario="${SMOKE_FAKE_SCENARIO:?missing scenario}"

poll_count=0
if [[ -f "$state_file" ]]; then
  poll_count="$(cat "$state_file")"
fi

if [[ "$url" == */health ]]; then
  printf '{"status":"ok"}\n'
  exit 0
fi

if [[ "$url" == */lectures/ingest ]]; then
  printf '{"lectureId":"smoke-lecture","audioPath":"storage/audio/smoke.wav"}\n'
  exit 0
fi

if [[ "$url" == */transcribe* ]]; then
  case "$scenario" in
    success|fallback)
      printf '{"jobId":"job-1","status":"queued","jobType":"transcription"}\n'
      ;;
    no_queued)
      printf '{"jobId":"job-1","status":"running","jobType":"transcription"}\n'
      ;;
    *)
      echo "unknown scenario: $scenario" >&2
      exit 9
      ;;
  esac
  exit 0
fi

if [[ "$url" == */jobs/job-1 ]]; then
  poll_count=$((poll_count + 1))
  printf '%s' "$poll_count" > "$state_file"
  case "$scenario:$poll_count" in
    success:1)
      printf '{"id":"job-1","status":"queued"}\n'
      ;;
    success:*)
      printf '{"id":"job-1","status":"succeeded","result":{"ok":true}}\n'
      ;;

    fallback:1)
      printf '{"id":"job-1","status":"queued"}\n'
      ;;
    fallback:*)
      printf '{"id":"job-1","status":"succeeded","result":{"queueFallback":"inline"}}\n'
      ;;


    no_queued:*)
      printf '{"id":"job-1","status":"succeeded","result":{"ok":true}}\n'
      ;;
    *)
      printf '{"id":"job-1","status":"queued"}\n'
      ;;
  esac
  exit 0
fi

echo "unexpected url: $url" >&2
exit 8
CURL
  chmod +x "$tmp/bin/curl"

  set +e
  PATH="$tmp/bin:$PATH" \
  API_BASE_URL="http://fake.local" \
  SMOKE_FAKE_SCENARIO="$scenario" \
  SMOKE_FAKE_STATE_FILE="$tmp/state" \
  SMOKE_TIMEOUT_SEC=5 \
  SMOKE_POLL_INTERVAL_SEC=0 \
  SMOKE_ALLOW_QUEUE_FALLBACK="$allow_fallback" \
  SMOKE_REQUIRE_QUEUED_TRANSITION="$require_transition" \
  "$SCRIPT" >/tmp/"$name".out 2>/tmp/"$name".err
  rc=$?
  set -e

  if [[ "$rc" != "$expect_code" ]]; then
    echo "FAIL[$name]: expected exit $expect_code, got $rc" >&2
    echo "--- stdout ---" >&2
    cat /tmp/"$name".out >&2 || true
    echo "--- stderr ---" >&2
    cat /tmp/"$name".err >&2 || true
    exit 1
  fi

  echo "PASS[$name]"
  rm -rf "$tmp"
  trap - RETURN
}

run_case "success" "success" 0
run_case "queue_fallback_detected" "fallback" 7
run_case "queue_fallback_allowed" "fallback" 0 1 1
run_case "never_queued" "no_queued" 6
run_case "never_queued_allowed_when_transition_optional" "no_queued" 0 0 0

echo "All smoke script logic tests passed"
