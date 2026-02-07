# Ingestion Stage

Purpose: accept uploads or recordings, store audio metadata, and create a Lecture record.

Inputs
- Course selection
- Lecture Style Preset selection
- Audio source metadata

Outputs
- Lecture record (`uploaded` status)
- Audio storage reference

Implementation note
- `pipeline/ingest_audio.py` provides a local MVP-style ingestion script that
  copies audio into `storage/audio` and writes lecture metadata to
  `storage/metadata`.
