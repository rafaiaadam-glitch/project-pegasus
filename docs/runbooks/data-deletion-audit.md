# Data Deletion Runbook (Lecture/Course) + Audit Trail

Use this runbook for all destructive deletion requests.

## Supported endpoints

- `DELETE /lectures/{lecture_id}`
- `DELETE /courses/{course_id}`

Optional query param:
- `purge_storage=true|false` (default `false`)

## Preconditions

1. Confirm requester authorization (owner/admin/support policy).
2. Confirm scope (single lecture vs full course).
3. Confirm whether storage purge is required by policy/legal request.
4. Capture ticket/change ID before executing.

## Execution

### Delete one lecture

```bash
curl -X DELETE "${API_BASE_URL}/lectures/${LECTURE_ID}?purge_storage=true" \
  -H "Authorization: Bearer ${PLC_WRITE_API_TOKEN}"
```

### Delete one course and cascade lectures

```bash
curl -X DELETE "${API_BASE_URL}/courses/${COURSE_ID}?purge_storage=true" \
  -H "Authorization: Bearer ${PLC_WRITE_API_TOKEN}"
```

## Validation checklist

After deletion:

1. `GET /lectures/{lecture_id}` returns `404` for removed lecture(s).
2. `GET /lectures/{lecture_id}/artifacts` returns `404` for removed lecture(s).
3. If `purge_storage=true`, verify object paths no longer exist in backing storage.
4. Confirm related jobs/exports/artifacts counts in delete response.

## Audit record template

Record every destructive deletion in your ticketing system with:

- Request ID / ticket ID
- Operator
- Timestamp (UTC)
- Endpoint used
- IDs deleted (course/lecture)
- `purge_storage` value
- API response payload
- Validation evidence (follow-up GET results, storage verification)

## Rollback expectations

Deletion is destructive and may be non-recoverable without backups.

If accidental deletion occurs:
- Follow `docs/runbooks/backup-restore.md`.
- Restore from latest verified backup into staging first.
- Validate integrity before production restoration.
