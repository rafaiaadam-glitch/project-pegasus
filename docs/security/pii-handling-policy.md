# PII Handling Policy for Transcripts and Artifacts

This policy defines minimum privacy controls for lecture content, transcripts, and generated study artifacts.

## Data classes

- **Raw audio**: uploaded recordings.
- **Transcripts**: text and segments derived from audio.
- **Artifacts**: summaries, flashcards, outlines, exam questions, exports.
- **Metadata**: course IDs, lecture IDs, timestamps, job status.

Treat raw audio and transcripts as **sensitive by default**.

## Collection and purpose limitation

- Collect only data required to run ingest → transcribe → generate → export.
- Do not repurpose transcript/artifact content for unrelated analytics without explicit product approval.

## Storage and access

- Store sensitive objects in controlled buckets/paths only.
- Use least-privilege IAM for API, worker, and operators.
- Restrict direct production data access to on-call/authorized operators.
- Never copy production transcript data into test fixtures unless anonymized.

## Retention

Pegasus enforces configurable retention cleanup (`python -m backend.retention`).

Recommended defaults:
- Raw audio: 30 days
- Transcript intermediates: 14 days
- Generated artifacts/exports: keep per product requirement; review quarterly

Any retention override must be documented with owner + expiration date.

## Redaction and sharing

- Do not paste full transcript excerpts into tickets/chat by default.
- For debugging, prefer:
  - lecture/job IDs,
  - timestamps,
  - short redacted snippets.
- If sharing examples externally, anonymize names, emails, phone numbers, IDs, and institution-specific identifiers.

## Deletion rights and workflows

Pegasus supports destructive deletion workflows:
- `DELETE /lectures/{lecture_id}`
- `DELETE /courses/{course_id}`

Use `purge_storage=true` when legal/product policy requires hard-deleting backing objects. Audit each deletion event per runbook in `docs/runbooks/data-deletion-audit.md`.

## Logging policy

- Logs must favor IDs over content.
- Do not log full transcripts/artifacts at info level.
- Include request/job identifiers to support auditing without leaking user content.

## Incident handling

If PII exposure is suspected:
1. Contain access (revoke credentials, limit access paths).
2. Rotate impacted secrets.
3. Identify affected lectures/courses and exposure window.
4. Execute deletion/remediation actions.
5. Document incident timeline and preventive follow-ups.
