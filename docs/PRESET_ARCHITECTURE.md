# 🎯 Preset Architecture - Strategic Design

## The Question

Should presets **only** affect extraction weighting (dice weights for thread detection)?

Or should they **also** control:
- Output formatting
- Collapse sensitivity
- Summary length
- Tone
- Generation parameters
- Export styles

## TL;DR Recommendation

**YES — Presets should be comprehensive system-wide profiles.**

Dice weights alone are powerful but limited. Full preset control unlocks:
- Coherent user experience across the entire pipeline
- Adaptive intelligence that matches learning context
- Reduced cognitive friction (students don't need to configure 10 settings)
- Product differentiation (competitors don't have this level of adaptive sophistication)

## Architecture Proposal

### Current State (Phase 1) ✅

```
Preset → Dice Weights → Thread Detection
```

Presets only influence **what concepts get extracted** and **with what priority**.

### Proposed State (Phase 2) 🎯

```
Preset → {
  Dice Weights          → Thread Detection
  Generation Config     → Artifact LLM prompts
  Output Formatting     → Section structure
  Summary Parameters    → Length, depth, style
  Tone Directives       → Language formality
  Export Preferences    → Default formats
  Collapse Sensitivity  → Thread merging thresholds
  Visual Styling        → Mobile UI presentation
}
```

Presets become **holistic learning mode profiles**.

## Detailed Impact Matrix

### 1. Thread Detection (Already Implemented ✅)

**Dice Weights** influence concept extraction priorities.

| Preset | Strongest Dimensions |
|--------|---------------------|
| Exam | What + How (50%) |
| Concept Map | How + Where + What (65%) |
| Beginner | What + How (65% — very strong grounding) |
| Neurodivergent | What + How + When (70% — structured stability) |
| Research | How + Where (45% — methodological focus) |
| Seminar | How + Who + Why (62% — argument-centric) |

### 2. Artifact Generation (Proposed)

**Generation Config** customizes LLM prompts for summaries, flashcards, exam questions.

#### Exam Mode Example:
```python
"generation_config": {
    "summary_max_length": 800,  # Concise for revision
    "flashcard_count": 25,      # High volume for memorization
    "question_types": ["definition", "explanation", "application"],
    "tone": "formal_academic",
    "include_mark_schemes": True,
    "emphasis": "examinable_points"
}
```

#### Beginner Mode Example:
```python
"generation_config": {
    "summary_max_length": 600,  # Shorter to avoid overwhelm
    "flashcard_count": 15,      # Focused essentials
    "question_types": ["recognition", "basic_understanding"],
    "tone": "conversational",
    "include_analogies": True,
    "emphasis": "foundational_clarity"
}
```

#### Neurodivergent Mode Example:
```python
"generation_config": {
    "summary_max_length": 400,  # Very concise
    "flashcard_count": 12,      # Minimal set
    "question_types": ["sequence", "recall"],
    "tone": "direct_predictable",
    "use_numbered_steps": True,
    "emphasis": "linear_structure"
}
```

### 3. Output Formatting (Proposed)

**Section Templates** control how artifacts are structured.

#### Current (Generic):
```json
{
  "sections": ["overview", "key_points", "details"]
}
```

#### Enhanced (Preset-Specific):

**Exam Mode:**
```json
{
  "sections": [
    "overview",
    "definitions_to_memorize",
    "examinable_mechanisms",
    "likely_exam_questions",
    "common_mistakes"
  ]
}
```

**Seminar Mode:**
```json
{
  "sections": [
    "main_claim",
    "supporting_argument",
    "counterargument",
    "critique",
    "discussion_questions"
  ]
}
```

**Concept Map Mode:**
```json
{
  "sections": [
    "core_nodes",
    "key_relationships",
    "dependency_chains",
    "system_boundaries"
  ]
}
```

### 4. Summary Length (Proposed)

**Length Targets** adapt to cognitive load preferences.

| Preset | Target Length | Rationale |
|--------|--------------|-----------|
| Exam | 600-800 words | Comprehensive but scannable |
| Beginner | 400-600 words | Avoids overwhelm |
| Neurodivergent | 300-500 words | Maximum clarity, minimal clutter |
| Research | 800-1200 words | Depth for critical analysis |
| Seminar | 700-1000 words | Room for argument development |
| Concept Map | 500-700 words | Focus on relationships |

### 5. Tone Directives (Proposed)

**Language Style** matches learning context.

| Preset | Tone Profile |
|--------|-------------|
| Exam | `formal_academic` — "The categorical imperative requires..." |
| Beginner | `conversational` — "Think of the categorical imperative like..." |
| Neurodivergent | `direct_predictable` — "Step 1: Identify the action. Step 2: Apply the test..." |
| Research | `analytical_precise` — "Kant's formulation posits a deontological framework wherein..." |
| Seminar | `dialectical` — "Kant argues... however, critics contend..." |

**Implementation:** System prompt includes tone directive:
```
TONE: Use conversational language with analogies. Avoid jargon.
```

### 6. Collapse Sensitivity (Proposed)

**Thread Merging Thresholds** control granularity.

Some presets want **fine-grained threads** (Concept Map, Research).
Others prefer **consolidated concepts** (Beginner, Neurodivergent).

| Preset | Merge Threshold | Behavior |
|--------|----------------|----------|
| Concept Map | 0.3 (low) | Keep threads separate for mapping |
| Research | 0.4 (low-medium) | Distinguish related concepts |
| Exam | 0.6 (medium-high) | Consolidate into exam topics |
| Beginner | 0.7 (high) | Reduce complexity |
| Neurodivergent | 0.8 (very high) | Maximum consolidation |
| Seminar | 0.5 (medium) | Balance positions vs. claims |

**Similarity score > threshold → merge threads**

### 7. Export Preferences (Proposed)

**Default Formats** match use case.

| Preset | Preferred Exports |
|--------|------------------|
| Exam | Anki (spaced repetition), PDF (revision notes) |
| Beginner | Markdown (readable), PDF (printable) |
| Neurodivergent | Markdown (accessible), Text (screen readers) |
| Research | Markdown (citation integration), PDF (sharing) |
| Seminar | Markdown (discussion prep), PDF (annotation) |
| Concept Map | *Future: Mermaid diagrams, GraphML* |

Mobile app could show preset-specific export suggestions.

### 8. Visual Styling (Proposed)

**Mobile UI Presentation** adapts to mode.

#### Neurodivergent Mode:
- High contrast
- Larger font
- Numbered lists (not bullets)
- Minimal emoji
- Predictable spacing

#### Beginner Mode:
- Friendly colors
- More visual breaks
- Analogy callouts
- Simplified icons

#### Exam Mode:
- Highlight key terms
- Mark scheme indicators
- Confidence ratings
- "Likely to be examined" badges

## Implementation Phases

### ✅ Phase 1: Dice Weights (Complete)
- Thread detection priorities
- System prompt customization
- All 6 presets configured

### 🎯 Phase 2A: Generation Customization (Recommended Next)
**Impact:** High | **Effort:** Medium

Add `generation_config` to presets:
```python
"generation_config": {
    "summary_max_length": 600,
    "flashcard_count": 20,
    "tone": "conversational",
    "emphasis": ["clarity", "examples"]
}
```

Pass to `llm_generation.py` to customize artifact prompts.

### 🎯 Phase 2B: Output Formatting (High Value)
**Impact:** High | **Effort:** Low

Already have `sections` in `outputProfile`.
Enhance artifact templates to use preset-specific sections.

### 🎯 Phase 2C: Collapse Sensitivity (Specialized)
**Impact:** Medium | **Effort:** Medium

Add `thread_merge_threshold` to presets.
Update thread continuity scoring to respect preset preference.

### 🎯 Phase 2D: Export Preferences (UX Polish)
**Impact:** Low | **Effort:** Low

Add `preferred_exports` to presets.
Show in mobile UI as "Recommended for this mode".

### 🎯 Phase 2E: Visual Styling (Accessibility)
**Impact:** High (for neurodiverse users) | **Effort:** High

Requires mobile UI theming system.
Defer until core functionality stable.

## Technical Architecture

### Preset Schema (Enhanced)

```python
{
    "id": "exam-mode",
    "name": "📝 Exam Mode",

    # Current (implemented)
    "diceWeights": { "what": 0.25, ... },
    "outputProfile": { "sections": [...], "chunking": "medium" },

    # Phase 2A (generation)
    "generation_config": {
        "summary_max_length": 800,
        "flashcard_count": 25,
        "tone": "formal_academic",
        "question_types": ["definition", "explanation"],
        "include_mark_schemes": True
    },

    # Phase 2B (formatting) — already exists
    "outputProfile": {
        "sections": ["overview", "examinable_points", ...],
        "section_templates": {
            "overview": "Concise summary of examinable content",
            "examinable_points": "Bullet list of key facts and mechanisms"
        }
    },

    # Phase 2C (thread control)
    "thread_config": {
        "merge_threshold": 0.6,
        "min_complexity": 2,  # Skip trivial threads
        "max_threads_per_lecture": 8
    },

    # Phase 2D (export)
    "export_preferences": {
        "recommended": ["anki", "pdf"],
        "default_format": "anki"
    },

    # Phase 2E (visual)
    "ui_theme": {
        "color_scheme": "high_contrast",
        "font_size": "large",
        "spacing": "comfortable"
    }
}
```

### Data Flow

```
User selects preset in mobile app
         ↓
Preset ID sent to /lectures/ingest
         ↓
Stored in lectures.preset_id (database)
         ↓
Jobs read preset configuration
         ↓
┌─────────────────────────────────────────┐
│ Thread Detection (dice weights)        │ ← Already implemented
├─────────────────────────────────────────┤
│ Artifact Generation (gen config)       │ ← Phase 2A
├─────────────────────────────────────────┤
│ Output Formatting (section templates)  │ ← Phase 2B
├─────────────────────────────────────────┤
│ Thread Merging (collapse threshold)    │ ← Phase 2C
└─────────────────────────────────────────┘
         ↓
Artifacts stored with preset metadata
         ↓
Export system reads preset preferences
         ↓
Mobile UI shows preset-optimized view
```

## Why This Matters

### 1. **Coherent Experience**
Students get a **holistic learning mode**, not a random mix of settings.

Bad: "I picked Exam Mode but the summary is too long and uses complex language"
Good: "Exam Mode gives me concise, formal summaries with mark schemes — perfect"

### 2. **Reduced Cognitive Load**
Students don't need to understand 15 different settings.
They just pick: "I'm studying for an exam" → Exam Mode handles everything.

### 3. **Adaptive Intelligence**
The system **understands context** and adapts at every level.
Not just "extract different threads" but "present them differently too".

### 4. **Accessibility**
Neurodivergent Mode becomes **genuinely supportive**, not just a label.
It controls: length, structure, sequencing, visual presentation, tone.

### 5. **Product Differentiation**
Competitors have "study modes" that just tweak flashcard counts.
Pegasus has **intelligent, context-aware learning profiles** that adapt the entire experience.

## Risks & Mitigations

### Risk 1: Preset Explosion
**Problem:** Too many presets, students confused.
**Mitigation:** Keep to 6-8 core presets. Allow custom presets later (advanced users).

### Risk 2: Over-Customization
**Problem:** Presets become too opinionated, limiting flexibility.
**Mitigation:** Presets are **defaults**, not locks. Advanced settings still available.

### Risk 3: Implementation Complexity
**Problem:** Too many moving parts.
**Mitigation:** **Phased rollout**. Ship Phase 2A (generation config) first, then iterate.

### Risk 4: Testing Burden
**Problem:** 6 presets × 5 artifact types × 3 export formats = 90 combinations.
**Mitigation:** Focus on **per-preset integration tests**, not exhaustive matrix.

## Recommendation

**Start with Phase 2A (Generation Customization):**

1. Add `generation_config` to all 6 presets
2. Update `llm_generation.py` to read and apply config
3. Test that Exam Mode produces different summaries than Beginner Mode
4. Ship it

**Then iterate:**
- Phase 2B (formatting) is easy — templates already exist
- Phase 2C (collapse) is specialized — defer until user feedback
- Phase 2D (export) is polish — low priority
- Phase 2E (UI) is long-term — accessibility roadmap

## Next Steps

1. **Decision:** Do you want to proceed with Phase 2A (generation customization)?
2. **Scope:** Which generation parameters should presets control? (summary length, tone, flashcard count, question types)
3. **Validation:** Should we A/B test preset effectiveness with real students?

---

**The Bottom Line:**

Presets are currently **smart thread detectors**.
They should become **intelligent learning mode orchestrators**.

This isn't scope creep — it's **system-level coherence**.
