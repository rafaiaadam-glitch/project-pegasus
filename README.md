# Project Pegasus

**Project Pegasus** is a modular AI “copilot” platform designed to turn unstructured knowledge (lectures, audiobooks, notes, conversations) into **structured understanding** over time.

Instead of producing isolated summaries, Pegasus builds **learning threads**: evolving concept maps that track how ideas develop across sessions, highlight what matters for exams or goals, and help users study **what to do next, when, and why**—while actively reducing cognitive overload.

---

## What this repo is for

This repository is the starting point for the **core platform** behind Pegasus. It will hold:

- Shared domain models (Concepts, Threads, Sources, Sessions)
- Ingestion pipelines (audio upload, transcription, segmentation)
- Knowledge extraction (key concepts, definitions, relationships)
- Thread-building logic (long-term continuity across sessions)
- Output formats (study plans, revision sheets, flashcards, Q&A)
- Guardrails to prevent overload (adaptive pacing + prioritisation)

If you’re looking for the product/app implementation (UI), this repo can support it—but the focus here is the **engine**.

---

## Core idea

Pegasus is built around one principle:

> Learning improves when we track **how** understanding changes over time, not just what was said once.

So Pegasus doesn’t just store notes. It maintains:

- **Sessions**: a lecture, chapter, meeting, or recording
- **Sources**: audio/video/text files and metadata
- **Concepts**: extracted topics, terms, and definitions
- **Threads**: living narratives of how concepts connect and evolve
- **Study Actions**: recommended next steps to learn efficiently

---

## Intended capabilities (MVP → V1)

### MVP (foundation)
- Upload audio (lecture/audiobook) → transcription
- Segment transcript into sections
- Extract key concepts + definitions
- Produce:
  - structured summary
  - bullet “skeleton outline”
  - exam-style questions
- Store everything as a session with metadata

### V1 (Pegasus-style differentiation)
- Detect repeated concepts across sessions
- Build persistent threads (“this keeps coming up”)
- Explain evolution: *what’s new vs repeated vs foundational*
- Generate study plan:
  - what to revise next
  - why it matters
  - how long it should take
- Overload prevention:
  - prioritisation
  - pacing
  - “stop here” suggestions when cognitive load is high

---

## Repository structure (planned)

