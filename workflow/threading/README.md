# Threading Stage

Purpose: detect and track recurring concepts across lectures.

Inputs
- Validated artifacts
- Existing Threads

Outputs
- ThreadOccurrence records with evidence
- ThreadUpdate records for evolution tracking
- Thread updates linked back to course/lecture

Implementation note
- `pipeline/thread_engine.py` implements lightweight term-based detection to
  create/update threads and capture occurrences per lecture.
