#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANARY_SCRIPT="$ROOT_DIR/scripts/canary_pipeline.sh"

TMP_DIR="$(mktemp -d)"
SERVER_LOG="$TMP_DIR/server.log"
PORT_FILE="$TMP_DIR/port"
STATE_FILE="$TMP_DIR/state.json"
SUMMARY_FILE="$TMP_DIR/summary.json"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cat > "$TMP_DIR/fake_canary_failure_server.py" <<'PY'
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

port_file = os.environ["PORT_FILE"]
state_file = os.environ["STATE_FILE"]

jobs = {
    "job-transcribe": ["queued", "running", "failed"],
}
job_polls = {k: 0 for k in jobs}

lecture_id = "canary-lecture-failure"
state = {
    "webhook": None,
    "deleted": False,
}

def save_state():
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump(state, fh)

class Handler(BaseHTTPRequestHandler):
    def _write_json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            self._write_json(200, {"status": "ok"})
            return

        if self.path.startswith("/jobs/"):
            job_id = self.path.split("/")[-1]
            states = jobs.get(job_id)
            if not states:
                self._write_json(404, {"detail": "job not found"})
                return
            idx = min(job_polls[job_id], len(states) - 1)
            status = states[idx]
            job_polls[job_id] += 1
            self._write_json(200, {"id": job_id, "status": status})
            return

        self._write_json(404, {"detail": "not found"})

    def do_POST(self):
        if self.path == "/lectures/ingest":
            self._write_json(200, {"lectureId": lecture_id, "status": "ingested"})
            return

        if self.path.startswith(f"/lectures/{lecture_id}/transcribe"):
            self._write_json(200, {"jobId": "job-transcribe", "status": "queued"})
            return

        if self.path == "/webhook":
            state["webhook"] = self._read_json()
            save_state()
            self._write_json(200, {"ok": True})
            return

        self._write_json(404, {"detail": "not found"})

    def do_DELETE(self):
        if self.path.startswith(f"/lectures/{lecture_id}"):
            state["deleted"] = True
            save_state()
            self._write_json(200, {"deleted": True})
            return
        self._write_json(404, {"detail": "not found"})

save_state()
server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
with open(port_file, "w", encoding="utf-8") as fh:
    fh.write(str(server.server_port))

server.serve_forever()
PY

PORT_FILE="$PORT_FILE" STATE_FILE="$STATE_FILE" python "$TMP_DIR/fake_canary_failure_server.py" >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

for _ in {1..50}; do
  if [[ -s "$PORT_FILE" ]]; then
    break
  fi
  sleep 0.1
done

if [[ ! -s "$PORT_FILE" ]]; then
  echo "FAIL: fake canary failure server did not start" >&2
  exit 1
fi

PORT="$(cat "$PORT_FILE")"
set +e
API_BASE_URL="http://127.0.0.1:$PORT" \
CANARY_LECTURE_ID="canary-lecture-failure" \
CANARY_TIMEOUT_SEC=20 \
CANARY_POLL_INTERVAL_SEC=0 \
CANARY_SUMMARY_FILE="$SUMMARY_FILE" \
CANARY_RESULT_WEBHOOK_URL="http://127.0.0.1:$PORT/webhook" \
CANARY_CLEANUP_LECTURE=1 \
"$CANARY_SCRIPT"
rc=$?
set -e

if [[ $rc -eq 0 ]]; then
  echo "FAIL: expected canary script failure, but it succeeded" >&2
  exit 1
fi

python - <<PY
import json
from pathlib import Path

summary = json.loads(Path('$SUMMARY_FILE').read_text())
assert summary['status'] == 'failed', summary
assert summary['failure']['stage'] == 'transcribe_poll', summary
assert summary['jobs']['transcribe'] == 'job-transcribe', summary
assert summary['timingsSec']['cleanup'] >= 0, summary

state = json.loads(Path('$STATE_FILE').read_text())
webhook = state['webhook']
assert webhook is not None, state
assert webhook['status'] == 'failed', webhook
assert webhook['failure']['stage'] == 'transcribe_poll', webhook
assert state['deleted'] is True, state
print('validation-ok')
PY

echo "Canary failure simulation passed"
