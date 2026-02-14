# Contributing to PLC (Pegasus Lecture Copilot)

Thank you for contributing to **Pegasus Lecture Copilot (PLC)**.

PLC is a concept-driven product.  
Contributions are welcome — **drift is not**.

This document exists to ensure that all contributions reinforce PLC’s core philosophy, not dilute it.

---

## Before you contribute (required reading)

You **must** read and understand:
- `README.md`
- `CODEX_SYSTEM_PROMPT.md` (if present)

If your contribution conflicts with either document, **the contribution is invalid**.

---

## What PLC is (and must remain)

PLC is:
- A **lecture-to-study-material pipeline**
- A **revision-first** system
- A tool that **reduces cognitive load**
- A system that **tracks concepts across time**

PLC is not a chatbot.
PLC is not a generic note app.
PLC is not an essay generator.

---

## Core principles (non-negotiable)

All contributions must uphold the following:

### 1. Structure over creativity
PLC prefers:
- Clear schemas
- Predictable formats
- Consistent outputs

Over:
- Free-form prose
- “Creative” summaries
- Chat-style responses

If an AI output cannot be validated against a schema, it does not belong in PLC.

---

### 2. Continuity over novelty
PLC’s defining feature is **concept continuity across lectures**.

Any feature that:
- Resets context every lecture
- Treats lectures as isolated blobs
- Ignores the Thread Engine

…violates the core product.

---

### 3. Reduce cognitive load
PLC exists to make studying easier, not more impressive.

Avoid:
- Extra configuration for users
- Overloaded UIs
- Optional complexity disguised as “power features”

If a feature increases mental effort without clear study benefit, it should not be added.

---

### 4. Presets are first-class citizens
Lecture Style Presets are not cosmetic.

Any feature involving AI output must:
- Respect preset selection
- Produce **visibly different results** per preset
- Be testable across presets

If presets do not meaningfully affect output, the feature is incomplete.

---

## The Thread Engine is sacred

The **Thread Engine** is not optional infrastructure.
It is not an enhancement.
It is not “future work.”

Any contribution that touches:
- Lecture processing
- Summarisation
- Concept extraction
- Study artifacts

Must consider:
- How does this affect threads?
- Does it strengthen or weaken cross-lecture continuity?

If the answer is “it doesn’t affect threads”, that is a red flag.

---

## Explicit non-goals (do NOT contribute)

Do not add:
- Chat-first interfaces
- “Ask anything” modes (MVP)
- AI conversations detached from lecture material
- Hallucinated citations
- Essay-writing or plagiarism-adjacent features
- Social feeds, likes, or comments
- Live lecture interaction features

If a feature feels like it belongs in ChatGPT or Notion, it probably does **not** belong in PLC.

---

## Contribution types we welcome

✅ Welcome:
- Improvements to lecture processing accuracy
- Better structuring of study artifacts
- Thread Engine robustness
- Export quality improvements
- Performance and cost optimisations
- Accessibility improvements
- Validation and error handling
- Test coverage
- Documentation clarity

⚠️ Discuss first:
- New presets
- Major UI changes
- New artifact types
- New data models

❌ Not welcome without explicit approval:
- New product directions
- Chat features
- “AI assistant” modes
- User-generated academic content

---

## Coding standards

- Prefer explicit schemas (JSON Schema, Zod, Pydantic, etc.)
- Validate all AI outputs
- Fail loudly on invalid data
- Avoid silent fallbacks
- Deterministic pipelines > clever heuristics

If AI output breaks schema, the correct response is:
- Retry
- Repair
- Or fail — **not** silently accept garbage

---

## Pull request checklist (required)

Before submitting a PR, confirm:

- [ ] This change aligns with the README philosophy
- [ ] This change does not weaken the Thread Engine
- [ ] Presets still meaningfully affect output
- [ ] Outputs remain revision-ready
- [ ] No new cognitive burden on users
- [ ] No chat-first patterns introduced
- [ ] Schemas are updated (if applicable)
- [ ] Tests or validation updated

PRs missing this checklist may be closed without review.

---

## How to propose bigger ideas

For substantial changes:
1. Open an issue
2. Describe:
   - The problem being solved
   - How it improves studying
   - How it interacts with threads
   - Why it does not add cognitive load
3. Wait for alignment before coding

PLC values **coherence over speed**.

---

## Final rule

If you are unsure whether a feature belongs in PLC, ask this:

> “Would this help a tired student revise more easily the night before an exam?”

If the answer is not a clear **yes**, do not ship it.

---

Thank you for helping build PLC the right way.
