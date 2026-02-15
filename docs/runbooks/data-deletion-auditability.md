# Data deletion workflow & auditability runbook

This runbook documents how to execute and verify lecture/course deletion using API endpoints with audit evidence.

## Endpoints

- `DELETE /lectures/{lecture_id}`
- `DELETE /courses/{course_id}`

Both support `purge_storage=true|false` (default `true`).

## Required headers (recommended for auditability)

- `x-request-id`: caller-generated correlation ID
- `x-actor-id`: operator identity performing deletion
- `Authorization: Bearer <token>` when `PLC_WRITE_API_TOKEN` is enabled

## Delete a lecture

```bash
curl -sS -X DELETE "$API_BASE_URL/lectures/$LECTURE_ID?purge_storage=true" \
  -H "x-request-id: del-lecture-001" \
  -H "x-actor-id: ops-user@example.com" \
  -H "Authorization: Bearer $PLC_WRITE_API_TOKEN"
```

Expected response contains:

- `deleted` counts (`lectures`, `artifacts`, `exports`, etc.)
- `auditEvent.eventType = "lecture.delete"`
- `auditEvent.requestId` and `auditEvent.actorId`
- `auditEvent.occurredAt`

## Delete a course

```bash
curl -sS -X DELETE "$API_BASE_URL/courses/$COURSE_ID?purge_storage=true" \
  -H "x-request-id: del-course-001" \
  -H "x-actor-id: ops-user@example.com" \
  -H "Authorization: Bearer $PLC_WRITE_API_TOKEN"
```

Expected response contains:

- `courseDeleted=true`
- `lectureDeletions[]` with per-lecture `deleted` counts
- top-level `auditEvent.eventType = "course.delete"`
- each nested lecture deletion includes `auditEvent.eventType = "lecture.delete"`

## Verification checklist

- [ ] API responses include expected `auditEvent` fields.
- [ ] Request IDs map to API logs for the deletion request.
- [ ] Actor ID is present in audit event payload and log context.
- [ ] Storage purge behavior matches `purge_storage` flag.

## Notes

- This runbook covers API-level auditability evidence.
- For compliance records, archive request/response samples and matching log entries from staging.
