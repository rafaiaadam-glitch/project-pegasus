# Pegasus Lecture Copilot

Pegasus Lecture Copilot is an AI-powered study assistant for university students that organizes learning around evolving **Threads** rather than static lecture notes. It focuses on helping students decide *what to study, when, and why* while actively preventing cognitive overload.

## Core rules
- **Threads are primary**: All study decisions are derived from thread gravity/confidence, not lecture order.
- **Lectures are immutable inputs**: Each lecture is a processed snapshot that feeds threads.
- **Layered depth**: Green → Yellow → Orange are available in the MVP. Deeper layers require explicit action and safeguards.
- **Ethics enforced**: Consent is mandatory; sources must be verified; no hallucinated citations or full essays.

## What is included
- Data models for lectures, threads, signals, and safeguards (`src/models.ts`).
- Scoring engine for gravity, confidence, and priority (`src/scoring.ts`).
- Processing helpers for lecture ingestion and thread updates (`src/pipeline.ts`).
- API helper contracts for uploads and daily study plans (`src/api.ts` + `src/endpoints.ts`).
- UI scaffolding for the “What to Study Today” view (`src/ui.tsx`).
- SQL schema aligned to the thread-first architecture (`db/schema.sql`).

## MVP scope
The MVP implements lecture upload, transcription ingestion, thread creation & extension, scoring, and the daily study view in green/yellow/orange layers.

## Non-goals
- Full essay drafting.
- Institutional dashboards.
- Advanced analytics beyond the core priority formula.
