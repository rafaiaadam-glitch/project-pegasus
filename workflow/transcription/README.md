# Transcription Stage

Purpose: convert lecture audio into a timestamped transcript.

Inputs
- Lecture record with audio source

Outputs
- Transcript payload (normalized for downstream processing)
- Lecture status update (`processing` -> `completed` on success)

Implementation note
- `pipeline/transcribe_audio.py` runs Whisper (if installed) and writes a
  timestamped transcript to `storage/transcripts/<lecture-id>.json`.
