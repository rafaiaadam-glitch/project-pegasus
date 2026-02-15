# PII Handling Policy (v1 baseline)

This policy defines how Project Pegasus handles transcript and generated artifact data that may contain personally identifiable information (PII).

## Data classes

1. **Raw audio uploads** — may contain direct identifiers.
2. **Transcripts** — may contain direct and indirect identifiers.
3. **Generated artifacts** (summary/flashcards/exam questions/etc.) — may repeat or infer identifiers from transcript input.
4. **Operational metadata** (job IDs, lecture IDs, timestamps) — typically low-risk but still sensitive in aggregate.

## Core policy

- Treat all transcript-adjacent content as sensitive by default.
- Collect the minimum data needed for product function.
- Retain sensitive data only as long as needed for workflow and support obligations.
- Restrict access to least privilege for operators and services.

## Storage and transmission controls

- Use HTTPS/TLS for all API/mobile traffic.
- Store artifacts in controlled storage buckets with restricted IAM policies.
- Avoid logging raw transcript content in application logs.
- Prefer structured logs with IDs over content payloads.

## Logging policy

Allowed in logs:

- request/job/lecture IDs
- status transitions
- duration, retry counts, and error classes

Disallowed in logs:

- raw transcript text
- full generated artifact body
- audio payload samples
- tokens/credentials

## Retention and deletion

- Follow configured retention lifecycle for raw uploads and intermediates.
- Provide deletion workflows for lectures/courses and associated artifacts.
- Deletion operations should be auditable (who/when/what scope).

## Access controls

- Restrict production data access to authorized operators only.
- Use separate credentials for local, staging, and production.
- Review IAM access periodically.

## Incident handling for PII exposure

1. Contain exposure (revoke credentials, disable offending path).
2. Assess scope (which records/logs/artifacts affected).
3. Rotate compromised secrets if applicable.
4. Remove exposed data where possible.
5. Document timeline, impact, and remediation.

## Team responsibilities

- Engineering: enforce technical controls and deletion pathways.
- Ops/SRE: monitor access, retention jobs, and alerting.
- Product/PM: ensure UX/legal messaging aligns with data handling reality.

## Verification checklist

- [ ] Logs sampled and verified free of transcript/artifact bodies.
- [ ] Retention job runs on schedule.
- [ ] Deletion workflow documented and tested in staging.
- [ ] Access review performed for production data stores.
