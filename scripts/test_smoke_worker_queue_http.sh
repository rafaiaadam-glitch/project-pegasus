#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE_SCRIPT="$ROOT_DIR/scripts/smoke_worker_queue.sh"

TMP_DIR="$(mktemp -d)"
SERVER_LOG="$TMP_DIR/server.log"
PORT_FILE="$TMP_DIR/port"
STATE_FILE="$TMP_DIR/state.json"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cat > "$TMP_DIR/fake_smoke_server.py" <<'PY'
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

state_file = os.environ["STATE_FILE"]
port_file = os.environ["PORT_FILE"]

state = {
    "polls": 0,
    "lecture_id": None,
    "job_id": "job-http-1",
}
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _write_json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            self._write_json(200, {"status": "ok"})
            return

        if self.path.startswith("/jobs/"):
            with lock:
                state["polls"] += 1
                polls = state["polls"]
            if polls == 1:
                payload = {"id": state["job_id"], "status": "queued"}
            else:
                payload = {
                    "id": state["job_id"],
                    "status": "succeeded",
                    "result": {"ok": True},
                }
            self._write_json(200, payload)
            return

        self._write_json(404, {"detail": "not found"})

    def do_POST(self):
        if self.path == "/lectures/ingest":
            with lock:
                state["lecture_id"] = "smoke-lecture-http"
            self._write_json(
                200,
                {
                    "lectureId": "smoke-lecture-http",
                    "audioPath": "storage/audio/smoke.wav",
                },
            )
            return

        if self.path.startswith("/lectures/") and self.path.endswith("/transcribe?model=base"):
            self._write_json(
                200,
                {
                    "jobId": state["job_id"],
                    "status": "queued",
                    "jobType": "transcription",
                },
            )
            return

        self._write_json(404, {"detail": "not found"})


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
with open(port_file, "w", encoding="utf-8") as fh:
    fh.write(str(server.server_port))
with open(state_file, "w", encoding="utf-8") as fh:
    json.dump(state, fh)

server.serve_forever()
PY

STATE_FILE="$STATE_FILE" PORT_FILE="$PORT_FILE" python "$TMP_DIR/fake_smoke_server.py" >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

for _ in {1..50}; do
  if [[ -s "$PORT_FILE" ]]; then
    break
  fi
  sleep 0.1
done

if [[ ! -s "$PORT_FILE" ]]; then
  echo "FAIL: fake smoke server did not start" >&2
  exit 1
fi

PORT="$(cat "$PORT_FILE")"
API_BASE_URL="http://127.0.0.1:$PORT" \
SMOKE_TIMEOUT_SEC=10 \
SMOKE_POLL_INTERVAL_SEC=0 \
"$SMOKE_SCRIPT"

echo "HTTP smoke simulation passed"
