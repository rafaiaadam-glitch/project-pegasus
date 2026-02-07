# Export Stage

Purpose: provide revision-ready exports.

Inputs
- Validated artifacts
- Course + Lecture metadata

Outputs
- PDF export
- Markdown export (Notion/Obsidian)
- Anki-compatible CSV export

Implementation note
- `pipeline/run_pipeline.py --export` writes Markdown, PDF, and Anki CSV to
  `storage/exports/<lecture-id>`.
