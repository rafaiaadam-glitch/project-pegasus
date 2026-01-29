# Pegasus Data Model

This document defines the **core persistent data structures** used by Project Pegasus.

The data model is designed to:
- Preserve learning history over time
- Support cross-session continuity
- Enable explainable recommendations
- Allow safe reprocessing and partial failures

Where possible, objects are **append-only**. Knowledge is accumulated, not overwritten.

---

## Design principles

1. **Append-first**
   - New understanding adds records instead of mutating history
2. **Separation of raw vs interpreted**
   - Transcripts ≠ concepts ≠ threads
3. **Traceability**
   - Every derived object links back to its source
4. **LLM-agnostic**
   - No hidden state inside prompts or models

---

## Core entities

---

## 1. Source

Represents a raw input provided by the user.

**Examples**
- Lecture audio file
- Audiobook chapter
- PDF or text notes

- 
