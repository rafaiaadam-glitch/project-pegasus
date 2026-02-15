# PII Handling Policy (Transcripts and Generated Artifacts)

This policy defines how Pegasus handles personal data in lecture inputs, transcripts, and generated artifacts.

## Scope

Applies to:

- Raw audio uploads
- Transcription outputs
- LLM-generated artifacts (summaries, flashcards, exam questions, key terms)
- Logs, exports, and operational evidence connected to lecture/course data

## Data classification

### PII-bearing content (restricted)

Treat all lecture-derived content as potentially sensitive and potentially PII-bearing:

- Audio files (voice can identify a person)
- Raw transcripts
- Generated artifacts containing names, emails, IDs, grades, health/financial/legal references, or other identifying context

### Operational metadata (internal)

- Lecture IDs, course IDs, job IDs, timestamps, status fields
- Storage paths and provider identifiers

Operational metadata is lower sensitivity than transcript content but is still internal and should not be publicly exposed.

## Handling requirements

### Collection and minimization

- Collect only fields needed for ingestion, processing, and retrieval.
- Avoid collecting unnecessary profile data in MVP paths.
- Use stable IDs (`course_id`, `lecture_id`) rather than personal identifiers when possible.

### Storage and encryption

- Use provider-managed encryption at rest for databases and object storage.
- Use TLS in transit for API and storage operations.
- Restrict bucket and database access to least-privilege service accounts.

### Access controls

- Limit production data access to authorized operators on a need-to-know basis.
- Require authenticated access for write operations and admin/ops endpoints.
- Avoid sharing transcript/artifact payloads in chat tools, tickets, or PRs.

### Logging and observability

- Do not log raw transcript text, audio bytes, or auth secrets.
- Prefer IDs and status codes for diagnostics.
- Redact or omit request bodies that may contain PII.

### Retention and deletion

- Follow configured retention lifecycle for raw uploads and intermediate artifacts.
- Support deletion workflows for lecture/course records and storage objects.
- Ensure deletion operations are auditable (who/when/what scope).

### Third-party processors

- Treat STT/LLM providers as data processors.
- Ensure provider usage aligns with contract and environment policy.
- Do not route production transcripts through unapproved tools/services.

## Incident handling (PII exposure)

If potential PII exposure is detected:

1. Contain access (revoke credentials, restrict endpoints, quarantine data path).
2. Rotate impacted secrets and redeploy services.
3. Assess scope: datasets, time window, and affected users/courses.
4. Preserve forensic logs/evidence.
5. Execute communication and remediation per incident runbook.

## Engineering checklist

- [ ] Transcript/artifact payloads are excluded from default logs.
- [ ] Data stores used by Pegasus enforce encryption at rest.
- [ ] Service accounts use least privilege for storage/database access.
- [ ] Retention jobs are enabled in production.
- [ ] Deletion workflow is documented and verified.
- [ ] Runbooks reference this policy.

## Related docs

- `docs/security/secrets-management.md`
- `docs/runbooks/incident-response.md`
- `docs/mvp-launch-checklist.md`
