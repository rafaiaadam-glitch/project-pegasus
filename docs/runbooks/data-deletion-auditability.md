# Data Deletion & Auditability Runbook

This runbook defines the supported deletion workflow for lectures/courses and how to audit destructive operations.

## Scope

- Delete a single lecture and all related artifacts/exports/jobs metadata.
- Delete a full course and all contained lectures.
- Verify audit logs for destructive operations.

## API endpoints

- `DELETE /lectures/{lecture_id}`
- `DELETE /courses/{course_id}`
- `GET /ops/deletion-audit`

## Auth + actor identity

All endpoints above honor write-token enforcement when `PLC_WRITE_API_TOKEN` is configured.

Optional request header to identify operator:

- `x-actor-id: <operator-or-service-id>`

Audit actor resolution:

1. Use `x-actor-id` when provided.
2. Else `authenticated` if Authorization header exists.
3. Else `anonymous`.

## Delete a lecture

```bash
curl -X DELETE \
  -H "Authorization: Bearer $PLC_WRITE_API_TOKEN" \
  -H "x-actor-id: ops-oncall" \
  "$API_URL/lectures/$LECTURE_ID?purge_storage=true"
```

Expected response includes deleted record counts and storage cleanup totals.

## Delete a course

```bash
curl -X DELETE \
  -H "Authorization: Bearer $PLC_WRITE_API_TOKEN" \
  -H "x-actor-id: ops-oncall" \
  "$API_URL/courses/$COURSE_ID?purge_storage=true"
```

Expected response includes per-lecture deletions and course deletion status.

## Verify deletion audit events

```bash
curl -H "Authorization: Bearer $PLC_WRITE_API_TOKEN" \
  "$API_URL/ops/deletion-audit?entity_type=lecture&entity_id=$LECTURE_ID&limit=20"
```

Audit event payload includes:

- `entity_type` (`lecture` or `course`)
- `entity_id`
- `action`
- `purge_storage`
- `actor`
- `request_id`
- `deleted_counts`
- `created_at`

## Failure mode note

Deletion audit writes are best-effort and non-blocking by design. If audit persistence fails, deletion operation can still return success, and API logs include `deletion.audit_write_failed` for incident follow-up.

## Post-delete checks

- `GET /lectures/{lecture_id}` returns `404` for deleted lecture.
- `GET /courses/{course_id}` returns `404` for deleted course.
- Audit list query returns matching deletion event(s).
