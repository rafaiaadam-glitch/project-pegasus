# Pegasus Architecture

This document describes the high-level architecture of **Project Pegasus**: an AI-powered learning engine that transforms unstructured inputs (lectures, audiobooks, notes) into structured, long-term learning threads and adaptive study guidance.

The architecture is **modular by design**, allowing components to be developed, swapped, or scaled independently.

---

## Architectural principles

1. **Separation of concerns**
   - Ingestion ≠ understanding ≠ planning
2. **Persistence over sessions**
   - Knowledge accumulates; it is never reset per upload
3. **Explainability**
   - Every recommendation should be traceable to evidence
4. **Overload-aware**
   - Output is intentionally throttled and prioritised
5. **LLM as component, not brain**
   - LLMs transform data; they do not own state

---

## High-level system flow

[ Input ]
|
v
[ Ingest ]
|
v
[ Transcription ]
|
v
[ Segmentation ]
|
v
[ Concept Extraction ]
|
v
[ Thread Engine ]
|
v
[ Study Planner ]
|
v
[ Outputs ]


Each stage produces **structured artifacts** that are stored and reused downstream.

---

## Core components

### 1. Ingest Layer

**Responsibility**
- Accept raw inputs and metadata

**Inputs**
- Audio files (mp3, wav, m4a)
- Text (PDF, markdown, notes)
- Metadata (course, date, source, author)

**Outputs**
- Normalised input record
- Pointer to raw asset storage

**Notes**
- No intelligence here
- Pure validation + storage registration

---

### 2. Transcription Layer

**Responsibility**
- Convert audio → text

**Inputs**
- Audio file reference

**Outputs**
- Verbatim transcript
- Timestamps (word or sentence level)
- Confidence scores (if available)

**Notes**
- Deterministic and repeatable
- Can be re-run with better models later

---

### 3. Segmentation Layer

**Responsibility**
- Break transcript into meaningful chunks

**Segmentation strategies**
- Time-based (e.g. every 2–5 minutes)
- Topic-shift detection
- Speaker change (if applicable)

**Outputs**
- Ordered segments with:
  - text
  - timestamps
  - session reference

**Why this matters**
Segmentation is the boundary between *raw speech* and *meaningful cognition*.

---

### 4. Concept Extraction Layer

**Responsibility**
- Identify what is being talked about

**Extracted entities**
- Concepts (terms, ideas, theories)
- Definitions
- Claims / arguments
- Examples
- Named authors or schools (esp. social sciences)

**Outputs**
Structured objects, e.g.:

```json
{
  "concept": "Social Constructionism",
  "definition": "...",
  "confidence": 0.82,
  "source_segment_id": "seg_014"
}



---
