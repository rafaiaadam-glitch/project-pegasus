# Generation Stage

Purpose: generate structured study artifacts based on the selected preset.

Inputs
- Transcript payload
- Lecture Style Preset
- Course + Lecture metadata

Outputs
- Structured summary
- Hierarchical outline
- Key terms & definitions
- Flashcards
- Exam-style questions

Implementation note
- `pipeline/run_pipeline.py --use-llm` uses OpenAI responses to generate
  schema-compliant artifacts when `OPENAI_API_KEY` is set.

All outputs must validate against `/schemas/artifacts/`.
