# PII Handling Policy (Transcripts & Generated Artifacts)

This policy defines how Pegasus Lecture Copilot (PLC) handles personally identifiable information (PII) across ingestion, transcription, artifact generation, export, and deletion.

## Scope

Applies to:
- Raw audio uploads
- Transcript files
- Generated artifacts (summary, outline, key terms, flashcards, exam questions)
- Export outputs (PDF/Markdown/CSV)
- Related metadata and logs

## Data classification

### 1) Direct identifiers (high sensitivity)
Examples:
- Full names
- Student IDs
- Email addresses
- Phone numbers

### 2) Indirect identifiers (moderate sensitivity)
Examples:
- Course + timestamp combinations tied to a specific user
- Unique lecture titles that identify a person

### 3) Operational metadata (low/moderate sensitivity)
Examples:
- Job IDs
- Request IDs
- Storage paths (must not encode user secrets)

## Handling rules

1. **Minimize collection**
   - Collect only what is required for lecture processing.
   - Do not store unnecessary identity fields in new schemas.

2. **Storage controls**
   - Keep transcript/artifact content in configured object storage paths.
   - Restrict storage and DB access by least-privilege service accounts.

3. **Transport controls**
   - Use HTTPS/TLS for all API and cloud service interactions.

4. **Logging controls**
   - Never log raw auth tokens or secrets.
   - Avoid logging full transcript/artifact payloads in production.
   - Prefer request IDs, job IDs, and lecture IDs for traceability.

5. **Access controls**
   - Enforce write protection (`PLC_WRITE_API_TOKEN`) where enabled.
   - Limit destructive operations to trusted operators/services.

6. **Retention + deletion**
   - Follow automated retention cleanup for raw/intermediate files.
   - Use deletion workflows to remove lecture/course data and verify audit records.

## Redaction guidance

When content excerpts are required for debugging or incident review:
- Redact names and email/phone/student identifiers.
- Share only minimum snippets required to diagnose the issue.
- Prefer synthetic sample data for reproductions.

## Incident response expectations

If PII exposure is suspected:
1. Contain access immediately (token rotation, access revocation).
2. Preserve audit/operational logs and request IDs.
3. Run deletion/remediation workflow for impacted records.
4. Document timeline, affected entities, and corrective actions.

## Verification checklist (operations)

- [ ] Write auth enabled in production (`PLC_WRITE_API_TOKEN`).
- [ ] No raw secrets in logs.
- [ ] Retention automation schedule configured.
- [ ] Deletion endpoints operational and auditable.
- [ ] Incident runbook includes PII response path.

## Related runbooks

- `docs/runbooks/incident-response.md`
- `docs/runbooks/backup-restore.md`
- `docs/runbooks/migration-rollback.md`
- `docs/runbooks/data-deletion-auditability.md`
- `docs/runbooks/observability-slos.md`
