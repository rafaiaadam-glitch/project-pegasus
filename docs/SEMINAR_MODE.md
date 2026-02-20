# 🎓 Seminar / Discussion Mode

## Overview

Seminar / Discussion Mode is a specialized preset optimized for debate-focused learning. It's designed for courses that emphasize argumentation, critical analysis, and discussion-based pedagogy.

## Target Disciplines

- Political Science
- Philosophy
- Law
- Sociology
- Anthropology
- Literature

## Dice Weights (Thread Detection Priorities)

The thread detection engine uses weighted priorities to identify relevant concepts:

| Dimension | Weight | Focus Area |
|-----------|--------|------------|
| **HOW** (Red) | 22% | Argument structure, methodology, logical flow |
| **WHO** (Blue) | 20% | Speakers, authors, schools of thought, attribution |
| **WHY** (Purple) | 20% | Normative claims, philosophical stakes, rationales |
| **WHAT** (Orange) | 18% | Core concepts, definitions, subject matter |
| **WHERE** (Green) | 12% | Geographic, institutional, contextual settings |
| **WHEN** (Yellow) | 8% | Historical context, temporal relationships |

**Total:** 100% (1.00)

## Optimization Goals

Seminar Mode optimizes for:

1. **Argument Clarity** - Clear identification of claims, premises, and conclusions
2. **Debate Tracking** - Following positions and counterpositions across discussions
3. **Position Mapping** - Identifying who holds which views
4. **Counterarguments** - Capturing opposing perspectives and critiques
5. **Normative Stakes** - Understanding "ought" claims and value judgments
6. **Speaker Attribution** - Tracking who said what and from which tradition

## Output Format

Unlike other modes, Seminar Mode produces specialized artifact sections:

1. **Main Claim** - The primary argument or thesis
2. **Supporting Argument** - Evidence and reasoning
3. **Counterargument** - Alternative or opposing views
4. **Critique** - Critical analysis and objections
5. **Open Question** - Unresolved issues for discussion

## Thread Engine Behavior

When Seminar Mode is active, the Thread Engine:

- Prioritizes **argument structure** (HOW: 22%) - traces logical flow and methodology
- Emphasizes **speaker attribution** (WHO: 20%) - identifies authors, schools of thought, and positions
- Tracks **normative claims** (WHY: 20%) - captures philosophical stakes and underlying values
- Records **core concepts** (WHAT: 18%) - notes key terms and definitions
- Notes **contextual settings** (WHERE: 12%) - geographic and institutional context
- Tracks **temporal relationships** (WHEN: 8%) - historical development and sequence

The system prompt is dynamically customized to guide the LLM toward these priorities.

## Technical Implementation

### Preset Configuration

```python
{
    "id": "seminar-mode",
    "name": "🎓 Seminar / Discussion Mode",
    "diceWeights": {
        "what": 0.18,
        "how": 0.22,
        "when": 0.08,
        "where": 0.12,
        "who": 0.20,
        "why": 0.20,
    },
    "outputProfile": {
        "summary_style": "debate_focused",
        "sections": [
            "main_claim",
            "supporting_argument",
            "counterargument",
            "critique",
            "open_question"
        ],
        "chunking": "argument_based"
    }
}
```

### Thread Detection

The thread engine accepts a `preset_id` parameter and uses it to:

1. Load the preset configuration from `backend/presets.py`
2. Build a customized system prompt using `_build_system_prompt(preset_config)`
3. Pass the enhanced prompt to the LLM (OpenAI)
4. Extract threads with emphasis on the specified dimensions

### System Prompt Enhancement

The base system prompt is augmented with:

```
MODE: 🎓 Seminar / Discussion Mode
Target disciplines: Political Science, Philosophy, Law, Sociology, Anthropology, Literature
Optimized for: Argument clarity, Debate tracking, Position mapping, ...

CONCEPT DETECTION PRIORITIES (dice weights):
- WHO (20%): Identify speakers, authors, schools of thought, and attribution
- WHY (20%): Track normative claims, philosophical stakes, and underlying rationales
- HOW (22%): Capture argument structure, methodology, and logical flow
- WHAT (18%): Record core concepts, definitions, and subject matter
- WHERE (12%): Note geographic, institutional, or contextual settings
- WHEN (8%): Track historical context and temporal relationships
```

## Usage

### Mobile App

When creating a lecture, select "🎓 Seminar / Discussion Mode" from the preset picker.

### API

```bash
curl -X POST http://localhost:8000/lectures/ingest \
  -F "audio=@lecture.mp3" \
  -F "course_id=phil-101" \
  -F "title=Kant's Categorical Imperative" \
  -F "preset_id=seminar-mode"
```

### Pipeline

```python
from pipeline.run_pipeline import run_pipeline, PipelineContext

context = PipelineContext(
    course_id="phil-101",
    lecture_id="lecture-001",
    preset_id="seminar-mode",
    generated_at="2026-02-15T12:00:00Z",
    thread_refs=[]
)

run_pipeline(
    transcript=transcript_text,
    context=context,
    output_dir=Path("storage/artifacts"),
    use_llm=True,
    llm_provider="openai"
)
```

## Comparison with Other Modes

| Feature | Research Mode | Exam Mode | Seminar Mode |
|---------|--------------|-----------|--------------|
| Primary Focus | Claims & evidence | Definitions & questions | Arguments & positions |
| WHO emphasis | Low | Low | **High** (20%) |
| WHY emphasis | Medium | Low | **High** (20%) |
| HOW emphasis | Medium | Low | **High** (22%) |
| Output Style | Argumentative | Concise academic | Debate-focused |
| Best For | Literature reviews | Test prep | Discussion seminars |

## Example Thread Detection

**Input Transcript (Philosophy):**
> "Kant argues that the categorical imperative is fundamentally different from hypothetical imperatives. While hypothetical imperatives are conditional—do X if you want Y—the categorical imperative commands unconditionally. Rawls later builds on this in his theory of justice..."

**Seminar Mode Detection:**
- **Main Thread:** "Categorical vs. Hypothetical Imperatives" (WHAT: 18%)
- **Speaker Attribution:** "Kant's deontology" (WHO: 20%)
- **Argument Structure:** "Unconditional moral commands" (HOW: 22%)
- **Normative Stake:** "Foundation of moral obligation" (WHY: 20%)
- **Intellectual Lineage:** "Kant → Rawls" (WHEN: 8%)

## Testing

Verify configuration:

```bash
python3 scripts/test_seminar_mode.py
```

Expected output:
- ✅ Dice weights sum to 1.00
- ✅ Preset loaded successfully
- ✅ System prompt includes mode-specific priorities

## Future Enhancements

1. **Citation Tracking** - Automatically link to source texts
2. **Debate Mapping** - Visual graph of argument relationships
3. **Position Profiles** - Aggregate views by author/school
4. **Dialectic Threads** - Track thesis-antithesis-synthesis patterns
5. **Normative Analysis** - Separate "is" from "ought" statements

## Related Documentation

- [Presets Guide](./PRESETS.md) - Overview of all available presets
- [Thread Engine](./THREAD_ENGINE.md) - How thread detection works
- [Dice Weights](./DICE_WEIGHTS.md) - Understanding the six-dimensional model
