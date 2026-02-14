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

Available presets:
- 📝 **Exam Mode** – definitions, examinable points, likely questions
- 🗺️ **Concept Map Mode** – hierarchies and relationships
- 👶 **Beginner Mode** – plain language and analogies
- 🧩 **Neurodivergent-Friendly Mode** – short chunks, low clutter
- 🔬 **Research Mode** – claims, arguments, evidence placeholders (methodological depth)
- 🎓 **Seminar Mode** – arguments, counterarguments, debate positions (argumentative structure)

**Seminar Mode** is specifically designed for seminar-heavy courses in:
- Political Science, Philosophy, Sociology
- Law, Literature, Anthropology
- Any discussion-based humanities or social science course

It emphasizes:
- 🔵 WHO (speakers, authors, schools of thought)
- 🟣 WHY (normative claims, philosophical stakes)
- 🔴 HOW (argument structure)
- 🟠 WHAT (core concepts)

And extracts: claims, evidence, counterclaims, critiques, and discussion questions.

Changing presets must result in **visibly different outputs**.

## Lecture Mode selection (before recording)

Before recording, users choose a broad **Lecture Mode** (no long subject list):
- 🧮 Mathematics / Formal
- 🔬 Natural Science
- 📊 Social Science
- 📚 Humanities / Philosophy
- 🧩 Interdisciplinary / Mixed Methods
- 🧠 Open / Mixed

UI guidance:
- Keep to these 6 broad options only
- Show a short helper line: “Different lecture types activate different reasoning dimensions.”
- Persist the selected mode as `lecture_mode` during ingest so backend metadata and downstream jobs can use it.
- AI provider settings are runtime-configurable (`llm_provider`, `llm_model`, transcription `provider`) to align with GCP deployments while preserving local fallbacks.

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

### Dice permutation control flow (mandatory)

Thread Engine execution order is controlled by the Dice permutation algorithm.

Source-of-truth files:
- `core/dice/permutations.json`
- `core/dice/courseModes.ts`
- `core/thread_engine/engine.ts`
- `core/thread_engine/rotate.ts`
- `core/thread_engine/facets.ts`

For each lecture segment and each thread update, the engine must:
1. Compute facet scores via `computeFacetScores(...)`
2. Select ordered faces via `rotatePerspective({ threadId, segmentIndex, facetScores, safeMode })`
3. Run facet extractors in the returned face order
4. Apply facet mutations only through `updateFacet(...)`

Safety rules:
- `safeMode` forces `ORANGE` then `RED` first (What → How)
- Collapse conditions override normal schedule and prioritise the weakest face first

Locked face mapping:
- `RED=How (1, South)`
- `ORANGE=What (2, Forward)`
- `YELLOW=When (3, North)`
- `GREEN=Where (4, Backward)`
- `BLUE=Who (5, West)`
- `PURPLE=Why (6, East)`

Mode-aware weighting profiles:
- **Mathematics / Formal** → WHAT 0.35, HOW 0.35, WHERE 0.20, WHEN 0.10, WHO 0.00, WHY 0.00
- **Natural Science** → WHAT 0.20, HOW 0.25, WHEN 0.15, WHERE 0.15, WHO 0.10, WHY 0.15
- **Social Science** → WHAT 0.15, HOW 0.20, WHEN 0.15, WHERE 0.15, WHO 0.20, WHY 0.15
- **Humanities / Philosophy** → WHAT 0.15, HOW 0.15, WHEN 0.10, WHERE 0.10, WHO 0.20, WHY 0.30
- **Open / Mixed** → all six faces weighted equally

When collapse is detected, priority uses weighted gap:
- `priority_i = weight_i × (maxScore - score_i)`

Interdisciplinary mode is **hybrid** and must run two extraction passes per segment:
1. Empirical pass (`HYBRID_WEIGHTS.EMPIRICAL`)
2. Interpretive pass (`HYBRID_WEIGHTS.INTERPRETIVE`)

Then merge outcomes into the same thread facets and use combined weights for collapse targeting.

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
- MVP→v1 launch execution checklist under `docs/mvp-launch-checklist.md`.

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
- Google Speech-to-Text (Vertex AI Speech) as primary; Whisper fallback for local/dev

**LLM**
- Gemini (Vertex AI / Google Generative Language API) as primary; OpenAI fallback

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

MIT (see [`LICENSE`](LICENSE)).
