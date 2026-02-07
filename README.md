# PLC — Pegasus Lecture Copilot

> You paid for the lecture. PLC makes sure you actually keep it.

Pegasus Lecture Copilot (PLC) is an AI-powered lecture processing system that converts recorded lectures into **structured, revision-ready study materials** while tracking how **concepts evolve across time** within a course.

PLC is **not** a generic transcription or note-taking app.  
It is a study companion designed to reduce cognitive load and improve long-term retention.

---

## Why PLC exists

Students lose most of what they hear in lectures because:
- Listening and note-taking compete for attention
- Notes are unstructured and inconsistent
- Concepts repeat across lectures without being connected
- Neurodivergent students are disproportionately affected

Most tools:
- Transcribe but don’t teach
- Summarise once and forget
- Produce generic output that still needs rewriting

PLC fixes this by focusing on **structure, continuity, and revision usability**.

---

## Core idea

PLC turns a lecture into **academic artifacts**, not just text.

From a single recording, PLC produces:
- Structured summaries
- Hierarchical outlines
- Key terms & definitions
- Flashcards
- Exam-style questions

Across multiple lectures, PLC tracks:
- Repeated concepts
- Refinements and contradictions
- Foundational vs advanced ideas

This cross-lecture continuity is called the **Thread Engine** and is central to the product.

---

## Target users

- University students
- Neurodivergent students (ADHD, dyslexia, autism)
- Lifelong learners attending long-form talks
- Postgraduate and theory-heavy courses

Design priority:
> Clarity over cleverness.  
> Structure over creativity.  
> Continuity over novelty.

---

## Core workflow (non-negotiable)

1. User creates or selects a **Course**
2. User selects a **Lecture Style Preset**
3. User records or uploads lecture audio
4. PLC processes the lecture automatically
5. PLC generates structured study materials
6. User reviews or exports immediately

If a step requires manual formatting by the user, the implementation is wrong.

---

## Lecture Style Presets (key differentiator)

Presets are selected **before recording** and must materially affect output structure.

Examples:
- **Exam Mode** – definitions, examinable points, likely questions
- **Concept Map Mode** – hierarchies and relationships
- **Beginner Mode** – plain language and analogies
- **Neurodivergent-Friendly Mode** – short chunks, low clutter
- **Research Mode** – claims, arguments, evidence placeholders

Changing presets must result in **visibly different outputs**.

---

## Thread Engine (core intelligence)

A **Thread** represents a concept that persists across lectures in a course.

The Thread Engine:
- Detects repeated concepts
- Tracks refinement, contradiction, or increasing complexity
- Links concepts to multiple lectures
- Flags foundational vs advanced ideas

Thread tracking is **not optional**.
It is the memory of the system.

---

## Exports

PLC supports:
- PDF (printable, clean)
- Markdown (Notion / Obsidian)
- Flashcard export (Anki-compatible CSV)

Outputs must be revision-ready without rewriting.

---

## Explicit non-goals

PLC is **not**:
- A chat-first AI assistant
- A generic note-taking app
- An essay or plagiarism tool
- A live lecture chatbot
- A social or collaborative platform (for MVP)

Do **not** add:
- Infinite chat UIs
- Open-ended “ask anything” modes in MVP
- Hallucinated citations
- AI-generated academic claims without grounding

---

## Quality bar

PLC output should feel like:
- A very good teaching assistant
- A revision guide, not a transcript
- Something a student could revise from immediately

If a student needs to rewrite the output before studying, the feature is incomplete.

---

## Engineering principles

- Structure beats cleverness
- Predictable output beats creativity
- Continuity beats novelty
- Prefer schemas, validation, and deterministic pipelines
- AI outputs must conform to strict JSON schemas
- Fail loudly on invalid or unstructured AI output

---

## Project status

PLC is under active development.

Early milestones:
- MVP lecture pipeline (audio → artifacts)
- Thread Engine v1
- Preset-driven outputs
- Export-ready study materials

## MVP implementation (current)

- Local pipeline scripts for ingestion, transcription, generation, threading, and exports.
- FastAPI backend scaffold under `backend/`.
- React Native (Expo) scaffold under `mobile/`.
- Deployment notes under `docs/deploy.md`.

---

## MVP stack (recommended)

**Frontend**
- React Native (Expo) **or** SwiftUI (if iOS-first polish is the priority)

**Backend**
- Node.js (Fastify/Express) **or** Python (FastAPI)

**Database**
- Postgres (Supabase is easiest for MVP)

**File storage**
- S3-compatible storage **or** Supabase Storage

**Jobs/queue**
- Simple worker (BullMQ/Redis) **or** serverless background jobs

**Transcription**
- Whisper (hosted API or self-hosted)

**LLM**
- OpenAI responses for structured generation

---

## 60-second data flow (definition of done)

Audio → Upload → Transcribe → Analyze → Generate artifacts → Store → Display/Export

---

## Guiding principle

> Reduce cognitive load.  
> Preserve knowledge.  
> Respect the lecture.

---

## License

TBD
