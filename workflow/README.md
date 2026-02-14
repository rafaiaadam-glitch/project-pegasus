# Workflow Scaffold

This scaffold maps the required PLC workflow into discrete, testable stages.
Each stage should be implemented as a deterministic step that accepts validated inputs
and produces schema-validated outputs.

## Stages

1. Ingestion
   - Accepts uploads or recordings and stores audio metadata.
   - Produces a Lecture record in `uploaded` status.

2. Transcription
   - Converts lecture audio into a transcript with timestamps.
   - Produces a normalized transcript artifact for downstream processing.

3. Generation
   - Produces structured study artifacts based on the selected preset.
   - Outputs must validate against the JSON schemas in `/schemas/artifacts/`.

4. Validation
   - Enforces JSON schema validation.
   - Fails loudly on invalid output.

5. Threading
   - Detects repeated concepts and links them to Threads.
   - Records ThreadOccurrence evidence and ThreadUpdate evolution entries.

6. Export
   - Produces PDF, Markdown, and Anki-compatible CSV outputs.

Each stage should be independently testable and idempotent.
