# Pegasus Roadmap (MVP → V1)

This roadmap turns the architecture into a build plan with concrete milestones and deliverables.

**Goal:** Ship an end-to-end learning pipeline fast (MVP), then add the differentiators that make Pegasus *Pegasus* (Threads + Overload-aware Study Planning).

---

## Definitions

- **MVP** = usable end-to-end system that produces structured learning outputs from an upload
- **V1** = persistent Threads + Study Planner + overload prevention + “what changed since last time”
- **Done** means:
  - data is stored
  - outputs are reproducible
  - failure modes don’t corrupt state
  - results are explainable and traceable to sources

---

## Phase 0 — Repo bootstrap (1–2 days)

**Deliverables**
- `README.md`
- `docs/architecture.md`
- `docs/data-model.md`
- `docs/roadmap.md` (this file)
- Folder scaffold:
src/pegasus/
ingest/
transcribe/
segment/
extract/
thread/
study/
storage/
api/

**Exit criteria**
- Anyone can open the repo and understand what will be built and where it lives.

---

## Phase 1 — MVP pipeline (Input → Outputs) (1–2 weeks)

### 1.1 Ingest
**Deliverables**
- Upload/register a Source (audio/text)
- Store metadata (course, title, date, tags)
- Object storage integration (local or S3 compatible)

**Exit criteria**
- A Source exists in storage + DB and is retrievable

---

### 1.2 Transcription
**Deliverables**
- Transcribe audio into text + timestamps
- Persist transcript as part of the Session artifacts
- Support reruns (new transcript version = new session or versioned transcript)

**Exit criteria**
- Given an mp3, system outputs transcript reliably

---

### 1.3 Segmentation
**Deliverables**
- Segment transcript into chunks
- Store segments with ordering + time bounds
- Basic strategies:
- time-based default
- optional topic-shift segmentation (later)

**Exit criteria**
- Any transcript becomes a list of segments (stable ordering)

---

### 1.4 Concept Extraction (schema-constrained)
**Deliverables**
- Extract Concepts per segment:
- terms, definitions, claims, examples, authors/theories
- Outputs are structured JSON objects validated against schema
- Confidence scores + traceability to Segment

**Exit criteria**
- A Session yields Concepts that can be inspected and queried

---

### 1.5 MVP Output Layer
**Deliverables**
For each Session, generate:
- Structured summary
- Skeleton outline
- Exam-style questions
- Export format (JSON + optional Markdown)

**Exit criteria**
- User can upload audio and receive useful study materials

---

## Phase 2 — Thread Engine (Core differentiator) (1–2 weeks)

### 2.1 Thread creation & matching
**Deliverables**
- Create Threads from Concepts across sessions
- Matching rules (start simple, improve later):
- exact label match
- synonym/embedding similarity (optional)
- author + concept co-occurrence boosts

**Exit criteria**
- The same concept in multiple sessions maps to a persistent Thread

---

### 2.2 Thread events (evolution tracking)
**Deliverables**
Generate a ThreadEvent for each Concept→Thread link:
- `first_appearance`
- `repetition`
- `refinement`
- `contradiction`

Also compute:
- novelty score
- exam relevance signals (basic heuristics)

**Exit criteria**
- Threads show a timeline of concept evolution across sessions

---

### 2.3 “What changed since last time”
**Deliverables**
- Change log view for any new session:
- new threads introduced
- threads repeated
- threads refined
- contradictions flagged

**Exit criteria**
- System produces a reliable delta summary after each new session

---

## Phase 3 — Study Planner (overload-aware guidance) (1–2 weeks)

### 3.1 Action generation
**Deliverables**
Generate StudyActions:
- `revise` (high repetition + exam weight)
- `deepen` (high novelty + foundational)
- `ignore` (low relevance / too detailed / tangential)

Include:
- priority score
- time estimate
- rationale tied to thread evidence

**Exit criteria**
- System outputs a ranked study plan after each session

---

### 3.2 Overload prevention rules
**Deliverables**
- Cap recommended actions per run (e.g. 5–10)
- Detect repetition fatigue (too many repeats without mastery)
- Suggest stopping points (“good enough for today”)
- Provide “minimum viable revision” mode for low energy days

**Exit criteria**
- Plans are short, realistic, and prevent infinite to-do lists

---

## Phase 4 — V1 hardening & UX outputs (1–2 weeks)

### 4.1 Explainability + traceability
**Deliverables**
- Every Thread summary links to events/segments
- Every StudyAction links to threads/sessions
- One-click evidence view (API-ready)

**Exit criteria**
- User can answer “why are you recommending this?” with receipts

---

### 4.2 Social-science friendly upgrades
**Deliverables**
- Better claim tracking:
- claim → evidence/example → counterclaim
- Author/school-of-thought clustering
- Contradiction handling becomes first-class (not an error)

**Exit criteria**
- Threads support arguments, perspectives, and disputes cleanly

---

### 4.3 API stabilization
**Deliverables**
- Public API spec (`docs/api.md`)
- Versioned endpoints
- Idempotent job execution
- Basic auth keys (or placeholder)

**Exit criteria**
- Frontend can be built cleanly against stable contracts

---

## Phase 5 — “Nice next” (Post-V1)

Optional but high leverage:
- Flashcard scheduler (spaced repetition)
- Personalised pacing by performance
- Multi-modal sources (slides + audio)
- Collaborative study groups
- Instructor mode (course-level concept maps)

---

## Milestone summary

**MVP**
- Upload → transcribe → segment → extract → outputs

**V1**
- Persistent Threads
- “What changed since last time”
- Study Planner with overload prevention
- Explainable recommendations + evidence links

---

## Immediate next actions (recommended)

1. Choose stack + storage approach (minimal decision)
2. Scaffold folders + basic CLI or API runner
3. Implement Phase 1 end-to-end (even if naive)
4. Only then optimise extraction + matching
