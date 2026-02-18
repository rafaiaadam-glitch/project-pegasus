# PII Handling Policy (Transcripts & Generated Artifacts)

## Purpose

This policy defines how Project Pegasus handles personally identifiable information (PII) in lecture audio, transcripts, and generated artifacts.

## Scope

Applies to:
- raw lecture audio uploads
- transcript files and transcript-derived metadata
- generated artifacts (summaries, flashcards, key terms, exams, outlines)
- export files produced from generated artifacts
- deletion/audit records related to destructive operations

## Data classification

- **High sensitivity**
  - Raw audio containing student/teacher speech
  - Full transcript text
- **Medium sensitivity**
  - Generated artifacts that may include names, institutions, or contextual identifiers from transcripts
- **Low sensitivity**
  - Operational metrics and health telemetry that do not include transcript text

## Handling rules

1. **Least access**
   - Access to storage buckets, DB records, and runtime logs must be restricted to service accounts and authorized operators.
2. **No transcript content in structured logs**
   - Application logs should contain IDs (request/job/lecture/course) and error categories, not raw transcript content.
3. **Audit destructive actions**
   - Lecture/course deletion operations must generate audit records that identify actor, entity, request id, and deletion counts.
4. **Retention enforcement**
   - Raw uploads and intermediate artifacts must be removed according to configured lifecycle/retention jobs.
5. **Secure transport/storage**
   - Use TLS for API transport and managed encrypted storage for persisted data.

## Deletion and user data rights

- Deletion endpoints:
  - `DELETE /lectures/{lecture_id}`
  - `DELETE /courses/{course_id}`
- Audit endpoint for deletion evidence:
  - `GET /ops/deletion-audit`
- Deletion requests should be executed with `purge_storage=true` unless an investigation hold applies.

## Operational controls

- Secrets must be supplied via environment/secret managers; never hardcoded in source.
- Production write-auth token (`PLC_WRITE_API_TOKEN`) must be enabled for destructive write endpoints.
- Alerting should notify on anomalous deletion spikes.

## Incident response expectations

If PII exposure is suspected:
1. Triage and scope impacted lecture/course IDs.
2. Rotate credentials/tokens involved in access paths.
3. Preserve relevant audit events and request IDs.
4. Execute containment + remediation from incident runbooks.
5. Publish post-incident corrective actions.

## Related implementation references

- `backend/app.py` (delete + deletion-audit endpoints)
- `backend/db.py` (deletion audit persistence/query)
- `backend/migrations/002_deletion_audit.sql` (audit table)
- `backend/retention.py` (retention automation)
- `docs/runbooks/incident-response.md`
