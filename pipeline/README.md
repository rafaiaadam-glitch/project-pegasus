# Pipeline Skeleton

This folder defines the placeholder pipeline structure for PLC.
Each stage is expected to validate inputs and produce schema-compliant outputs.

Stages:
- ingestion
- transcription
- generation
- validation
- threading
- export

Each stage should be deterministic and idempotent.

## Minimal runner

`run_pipeline.py` is a minimal, schema-validated runner that generates stub
artifacts from a transcript, emits Thread Engine v1 records, and writes them to
`pipeline/output/<lecture-id>`.

The input can be a plain text transcript or a JSON transcript with a `text`
field (as produced by `transcribe_audio.py`).

```bash
python pipeline/run_pipeline.py \
  --input pipeline/inputs/sample-transcript.txt \
  --course-id course-001 \
  --lecture-id lecture-001 \
  --preset-id exam-mode
```

The runner validates each artifact against the JSON schemas under
`schemas/artifacts` and validates thread records against `schemas/`. It exits
with a clear error if any output fails validation.
Validation is handled by a lightweight, built-in checker so the runner works
offline without installing dependencies.

### LLM-backed generation

Use `--use-llm` to generate artifacts with OpenAI (requires `OPENAI_API_KEY`):

```bash
OPENAI_API_KEY=... python pipeline/run_pipeline.py \
  --input storage/transcripts/lecture-001.json \
  --course-id course-001 \
  --lecture-id lecture-001 \
  --preset-id exam-mode \
  --use-llm
```

## Audio ingestion + storage (MVP step)

`ingest_audio.py` copies a lecture audio file into durable storage and writes
lecture metadata for downstream processing.

```bash
python pipeline/ingest_audio.py \
  --input path/to/lecture-audio.mp3 \
  --course-id course-001 \
  --lecture-id lecture-001 \
  --preset-id exam-mode \
  --title "Lecture 1: Cellular Respiration" \
  --duration-sec 3600 \
  --source-type upload
```

This writes:
- `storage/audio/<lecture-id>.<ext>` (the stored audio file)
- `storage/metadata/<lecture-id>.json` (lecture metadata with checksum)

## Transcription (Whisper)

`transcribe_audio.py` runs Whisper (if installed) and writes a timestamped
transcript for downstream generation.

```bash
python pipeline/transcribe_audio.py \
  --input storage/audio/lecture-001.mp3 \
  --lecture-id lecture-001 \
  --model base
```

This writes:
- `storage/transcripts/<lecture-id>.json` (timestamped transcript segments)

## Exports (Markdown, PDF, Anki CSV)

Run with `--export` to emit Markdown, PDF, and Anki CSV outputs:

```bash
python pipeline/run_pipeline.py \
  --input pipeline/inputs/sample-transcript.txt \
  --course-id course-001 \
  --lecture-id lecture-001 \
  --preset-id exam-mode \
  --export
```

Exports are written to `storage/exports/<lecture-id>`.

### Preset-driven output examples

Change `--preset-id` to see different output structures:

- `exam-mode` emphasizes examinable points and exam-style questions.
- `concept-map-mode` focuses on relationships and hierarchy.
- `beginner-mode` uses simpler definitions and plain language.
- `neurodivergent-friendly` uses short, low-clutter chunks.
- `research-mode` adds evidence placeholders and open questions.
