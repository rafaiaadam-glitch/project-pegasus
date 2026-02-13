#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
LECTURE_ID="${LECTURE_ID:-}"
LIMIT="${LIMIT:-100}"
AUTH_HEADER="${AUTH_HEADER:-}"

query="limit=${LIMIT}&offset=0"
if [[ -n "${LECTURE_ID}" ]]; then
  query="lecture_id=${LECTURE_ID}&${query}"
fi

curl_args=(-fsS)
if [[ -n "${AUTH_HEADER}" ]]; then
  curl_args+=(-H "Authorization: ${AUTH_HEADER}")
fi

failed_payload=$(curl "${curl_args[@]}" "${API_BASE_URL}/jobs/failed?${query}")

job_ids=$(python - <<'PY' "$failed_payload"
import json,sys
payload=json.loads(sys.argv[1])
for job in payload.get("jobs",[]):
    jid=job.get("id")
    if jid:
        print(jid)
PY
)

if [[ -z "${job_ids}" ]]; then
  echo "No failed jobs to replay"
  exit 0
fi

count=0
while IFS= read -r job_id; do
  [[ -z "$job_id" ]] && continue
  curl "${curl_args[@]}" -X POST "${API_BASE_URL}/jobs/${job_id}/replay" >/dev/null
  echo "Replayed failed job: ${job_id}"
  count=$((count+1))
done <<< "${job_ids}"

echo "Replay complete (${count} jobs)"
