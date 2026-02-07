# Data Model (Initial)

This document defines the initial entities and relationships required for Pegasus Lecture Copilot.
The goal is to make the core workflow and Thread Engine explicit, while keeping the model small and strict.

## Entities

### Course
A collection of lectures.

**Fields**
- `id` (string, required): Unique identifier.
- `name` (string, required): Course name.
- `description` (string, optional): Short description.
- `createdAt` (string, required): ISO 8601 timestamp.
- `updatedAt` (string, required): ISO 8601 timestamp.

**Relationships**
- One Course → Many Lectures
- One Course → Many Threads

---

### Lecture
A single lecture recording within a course.

**Fields**
- `id` (string, required)
- `courseId` (string, required)
- `presetId` (string, required): Lecture Style Preset selected before recording.
- `title` (string, required)
- `recordedAt` (string, required): ISO 8601 timestamp.
- `durationSec` (number, required)
- `audioSource` (object, required): Metadata about recording/upload source.
- `status` (string, required): `uploaded | processing | completed | failed`.
- `artifacts` (array, optional): References to generated artifacts.

**Relationships**
- Many Lectures → One Course
- Many Lectures → One Preset
- One Lecture → Many Artifacts
- One Lecture → Many Thread links (via Artifacts/ThreadRefs)

---

### LectureStylePreset
Defines how outputs are structured and chunked.

**Fields**
- `id` (string, required)
- `name` (string, required)
- `kind` (string, required): Enumerated preset type, e.g. `exam | concept-map | beginner | neurodivergent | research | custom`.
- `description` (string, optional)
- `outputProfile` (object, required): Preset-specific structural settings used by generation.

**Relationships**
- One Preset → Many Lectures

---

### Thread
A concept that persists across lectures in a course.

**Fields**
- `id` (string, required)
- `courseId` (string, required)
- `title` (string, required): Canonical concept name.
- `summary` (string, required): Short evolving description.
- `status` (string, required): `foundational | advanced`.
- `complexityLevel` (integer, required): 1–5 scale.
- `lectureRefs` (array, required): Lecture IDs where the concept appears.
- `evolutionNotes` (array, optional): Structured notes about refinement/contradiction.

**Relationships**
- Many Threads → One Course
- Many Threads ↔ Many Lectures

---

### ThreadOccurrence
An occurrence of a Thread inside a specific lecture artifact.

**Fields**
- `id` (string, required)
- `threadId` (string, required)
- `courseId` (string, required)
- `lectureId` (string, required)
- `artifactId` (string, required)
- `evidence` (string, required): Short grounded excerpt or paraphrase tied to the lecture content.
- `confidence` (number, required): 0–1 score.
- `capturedAt` (string, required): ISO 8601 timestamp.

**Relationships**
- Many Occurrences → One Thread
- Many Occurrences → One Lecture
- Many Occurrences → One Artifact

---

### ThreadUpdate
An atomic change log entry describing how a Thread evolved in a lecture.

**Fields**
- `id` (string, required)
- `threadId` (string, required)
- `courseId` (string, required)
- `lectureId` (string, required)
- `changeType` (string, required): `refinement | contradiction | complexity`.
- `summary` (string, required): One-sentence summary of the change.
- `details` (array, optional): Bullet points describing the change.
- `capturedAt` (string, required): ISO 8601 timestamp.

**Relationships**
- Many Updates → One Thread
- Many Updates → One Lecture

---

### Artifact
Structured, revision-ready outputs for a lecture.

Artifacts are stored as separate documents by type:
- Structured Summary
- Hierarchical Outline
- Key Terms & Definitions
- Flashcards
- Exam-style Questions

All artifacts share common metadata:
- `id`
- `courseId`
- `lectureId`
- `presetId`
- `artifactType`
- `generatedAt`
- `version`
- `threadRefs` (optional): Thread IDs linked to this artifact

Each artifact has a strict JSON schema defined under `/schemas/artifacts/`.

---

## Core Workflow Mapping

1. Course is created.
2. User selects Lecture Style Preset.
3. Lecture is recorded or uploaded.
4. Lecture is processed.
5. Artifacts are generated and linked to Threads.

The data model above is designed to support this flow without manual formatting.
