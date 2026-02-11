# Pipeline

This folder defines the pipeline structure for PLC (Pegasus Lecture Copilot).
Each stage validates inputs and produces schema-compliant outputs.

**Stages:**
- Ingestion
- Transcription
- Generation
- Validation
- Threading
- Export

Each stage is deterministic and idempotent.

---

## Quick Start

### Installation

```bash
# Install required dependencies
pip install -r pipeline/requirements.txt
```

**Dependencies:**
- `jsonschema>=4.20.0` - JSON Schema validation

### Basic Usage

```bash
python pipeline/run_pipeline.py \
  --input pipeline/inputs/sample-transcript.txt \
  --course-id course-001 \
  --lecture-id lecture-001 \
  --preset-id exam-mode
```

**Output:**
```
[0/3] Starting: thread_generation...
✓ thread_generation (2.3s)
[1/3] Starting: artifact_generation...
✓ artifact_generation (5.1s)
[2/3] Starting: validation_and_save...
✓ validation_and_save (0.4s)

============================================================
PIPELINE EXECUTION SUMMARY
============================================================
  DONE         thread_generation                2.3s
  DONE         artifact_generation              5.1s
  DONE         validation_and_save              0.4s
============================================================
Total duration: 8.2s
Steps: 3 succeeded, 0 failed
============================================================
Artifacts written to pipeline/output/lecture-001
```

---

## Pipeline Runner (`run_pipeline.py`)

The main pipeline runner generates structured study artifacts from lecture transcripts:

### What it Generates

From a single transcript, the pipeline produces:
- **Summary** - Structured overview with key sections
- **Outline** - Hierarchical topic breakdown
- **Key Terms** - Definitions with examples
- **Flashcards** - Study cards with difficulty levels
- **Exam Questions** - Practice questions with answers
- **Threads** - Cross-lecture concept tracking
- **Thread Occurrences** - Where concepts appear
- **Thread Updates** - How concepts evolve

All outputs are **validated against JSON schemas** and written to `pipeline/output/<lecture-id>/`.

### Input Formats

Accepts:
- Plain text transcripts (`.txt`)
- JSON transcripts with `text` field (from `transcribe_audio.py`)

### Command Line Options

```bash
python pipeline/run_pipeline.py --help
```

**Options:**
- `--input PATH` - Path to transcript (default: `pipeline/inputs/sample-transcript.txt`)
- `--course-id ID` - Course identifier (default: `course-001`)
- `--lecture-id ID` - Lecture identifier (default: `lecture-001`)
- `--preset-id ID` - Preset mode (default: `exam-mode`)
- `--use-llm` - Use OpenAI for generation (requires `OPENAI_API_KEY`)
- `--openai-model MODEL` - OpenAI model to use (default: `gpt-4o-mini`)
- `--export` - Export to Markdown, PDF, and Anki CSV
- `--output-dir PATH` - Output directory (default: `pipeline/output`)

---

## Presets (Lecture Style Modes)

Presets materially affect output structure and content. Each preset produces **visibly different outputs** optimized for different learning styles and use cases.

### Available Presets

#### `exam-mode` (Default)
Focuses on examinable content and test preparation.
- Exam-focused summaries
- Essential definitions
- Practice questions (multiple-choice, essay, short-answer)
- Exam preparation flashcards

#### `beginner-mode`
Plain-language explanations for learners new to the topic.
- Simple, accessible language
- Core concepts emphasized
- Real-world examples and analogies
- "Big idea" and "Why it matters" sections

#### `research-mode`
Academic rigor with evidence tracking.
- Claim-focused summaries
- Evidence placeholders `[evidence]`
- Open research questions
- Citations and references support

#### `concept-map-mode`
Emphasizes relationships and hierarchies.
- Network of interconnected concepts
- Relationship-first summaries
- Hierarchical outlines
- Cross-lecture connections highlighted

#### `neurodivergent-friendly-mode`
Low-clutter, structured content for neurodivergent students.
- Short, focused chunks
- Clear checkpoints
- Reduced cognitive load
- Simplified flashcards

### Preset Example Comparison

**Same transcript, different presets:**

```bash
# Exam mode - test preparation
python pipeline/run_pipeline.py --preset-id exam-mode --lecture-id test-exam

# Beginner mode - accessible learning
python pipeline/run_pipeline.py --preset-id beginner-mode --lecture-id test-beginner

# Research mode - academic depth
python pipeline/run_pipeline.py --preset-id research-mode --lecture-id test-research
```

Compare outputs:
```bash
diff pipeline/output/test-exam/summary.json pipeline/output/test-beginner/summary.json
```

---

## Architecture & Recent Improvements

### Schema Validation (Feb 2026)

**Before:** 342 lines of manual validation code
**After:** JSON Schema validation with `jsonschema` library

The pipeline uses the `jsonschema` library for robust validation:
- **98% code reduction** (342 lines → 8 lines)
- Industry-standard JSON Schema Draft 2020-12
- Clear, actionable error messages
- All schemas in `schemas/artifacts/` and `schemas/`

**Implementation:**
```python
from pipeline.schema_validator import SchemaValidator

validator = SchemaValidator(schema_dir)
validator.validate(artifact, "summary.schema.json")
```

### Progress Tracking (Feb 2026)

Real-time feedback during pipeline execution:
- Step-by-step progress updates
- Timing for each stage
- Summary report with success/failure counts
- Clear status indicators (✓ for success, ✗ for failure)

**Implementation:**
```python
from pipeline.progress_tracker import ProgressTracker

tracker = ProgressTracker(total_steps=3, verbose=True)
tracker.start_step("thread_generation")
# ... do work ...
tracker.complete_step("thread_generation")
tracker.print_summary()
```

### Retry Logic & Error Handling (Feb 2026)

Robust API call handling with exponential backoff:
- **3 retry attempts** with configurable delays
- Exponential backoff: 2s → 4s → 8s
- Smart retry logic:
  - ✅ Retry on: HTTP 429 (rate limit), 5xx (server errors), network errors
  - ❌ Fail immediately on: HTTP 400, 401, 403 (client errors)
- Clear error reporting

**Implementation:**
```python
from pipeline.retry_utils import with_retry, RetryConfig

config = RetryConfig(max_attempts=3, initial_delay=2.0)
result = with_retry(make_api_call, config=config, operation_name="API request")
```

### Thread Reference Consistency (Feb 2026)

**Before:** Thread IDs hardcoded as `["thread-neuron-signaling", "thread-ion-channels"]`
**After:** Real UUIDs from generated threads

The pipeline now generates threads **first**, then uses actual UUIDs in artifacts:

**Execution order:**
1. Generate threads → Get real UUIDs (e.g., `b3d7250f-5901-4c41-91e3-1cb66c08c18f`)
2. Extract thread IDs from generated threads
3. Pass real IDs to artifact generators
4. Artifacts reference actual threads (data consistency ✓)

### Generic Content Templates (Feb 2026)

**Before:** ~350 lines of hardcoded neuroscience-specific examples
**After:** Generic, preset-driven templates

Content is now:
- **Generic** - Works for any subject matter
- **Preset-driven** - Different presets → different structures
- **Reusable** - Easy to extend with new presets
- **Maintainable** - 91% code reduction (350 → 30 lines)

**Implementation:**
```python
from pipeline.content_templates import get_summary_template

template = get_summary_template(preset_id, lecture_id)
artifact.update(template)
```

---

## LLM-Backed Generation

Use OpenAI for intelligent artifact generation instead of templates:

```bash
export OPENAI_API_KEY="your-api-key"

python pipeline/run_pipeline.py \
  --input storage/transcripts/lecture-001.json \
  --course-id course-001 \
  --lecture-id lecture-001 \
  --preset-id exam-mode \
  --use-llm \
  --openai-model gpt-4o-mini
```

**Features:**
- Automatic retry with exponential backoff
- Preset-aware prompts
- Schema-validated output
- Thread reference integration

**Supported models:**
- `gpt-4o-mini` (default, cost-effective)
- `gpt-4o` (higher quality)
- `gpt-4-turbo`

---

## Audio Ingestion

`ingest_audio.py` stores lecture audio files and metadata:

```bash
python pipeline/ingest_audio.py \
  --input path/to/lecture-audio.mp3 \
  --course-id course-001 \
  --lecture-id lecture-001 \
  --preset-id exam-mode \
  --title "Lecture 1: Introduction" \
  --duration-sec 3600 \
  --source-type upload
```

**Outputs:**
- `storage/audio/<lecture-id>.<ext>` - Stored audio file
- `storage/metadata/<lecture-id>.json` - Lecture metadata with checksum

---

## Transcription (Whisper)

`transcribe_audio.py` converts audio to timestamped transcripts:

```bash
python pipeline/transcribe_audio.py \
  --input storage/audio/lecture-001.mp3 \
  --lecture-id lecture-001 \
  --model base
```

**Requires:** Whisper installed (`pip install openai-whisper`)

**Outputs:**
- `storage/transcripts/<lecture-id>.json` - Timestamped transcript segments

**Whisper models:**
- `tiny` - Fastest, lowest accuracy
- `base` - Good balance (recommended)
- `small` - Better accuracy
- `medium` - High accuracy
- `large` - Best accuracy, slowest

---

## Exports

Export artifacts to multiple formats for different study workflows:

```bash
python pipeline/run_pipeline.py \
  --input pipeline/inputs/sample-transcript.txt \
  --course-id course-001 \
  --lecture-id lecture-001 \
  --preset-id exam-mode \
  --export
```

**Export formats:**
- **Markdown** - Human-readable study notes
- **PDF** - Print-ready documents
- **Anki CSV** - Import flashcards to Anki

**Outputs:** `storage/exports/<lecture-id>/`

---

## Module Reference

### Core Modules

**`run_pipeline.py`**
- Main pipeline orchestrator
- Artifact generation and validation
- Progress tracking integration
- Thread generation coordination

**`schema_validator.py`** *(new, Feb 2026)*
- JSON Schema validation wrapper
- Schema caching for performance
- Clear error messages

**`progress_tracker.py`** *(new, Feb 2026)*
- Step-by-step progress tracking
- Timing and performance monitoring
- Summary report generation

**`retry_utils.py`** *(new, Feb 2026)*
- Exponential backoff retry logic
- Smart error classification
- Configurable retry behavior

**`content_templates.py`** *(new, Feb 2026)*
- Generic artifact templates
- Preset-driven content generation
- Easy extension for new presets

**`llm_generation.py`**
- OpenAI integration
- Retry logic for API calls
- Prompt engineering for presets

**`thread_engine.py`**
- Cross-lecture concept tracking
- Thread detection and evolution
- Fallback extraction without LLM

**`export_artifacts.py`**
- Multi-format export (Markdown, PDF, Anki)
- Template-based rendering

**`ingest_audio.py`**
- Audio file storage
- Metadata generation with checksums

**`transcribe_audio.py`**
- Whisper integration
- Timestamped transcript generation

---

## Testing

Run the pipeline with different configurations:

```bash
# Test basic generation
python pipeline/run_pipeline.py --lecture-id test-basic

# Test all presets
for preset in exam-mode beginner-mode research-mode concept-map-mode neurodivergent-friendly-mode; do
  python pipeline/run_pipeline.py --preset-id $preset --lecture-id test-$preset
done

# Test with exports
python pipeline/run_pipeline.py --export --lecture-id test-export

# Test LLM generation (requires API key)
OPENAI_API_KEY=... python pipeline/run_pipeline.py --use-llm --lecture-id test-llm
```

**Verify outputs:**
```bash
# Check all artifacts generated
ls -la pipeline/output/test-basic/

# Verify thread references match
cat pipeline/output/test-basic/threads.json | grep '"id"' | head -3
cat pipeline/output/test-basic/summary.json | grep 'threadRefs' -A 3

# Compare preset outputs
diff pipeline/output/test-exam-mode/summary.json \
     pipeline/output/test-beginner-mode/summary.json
```

---

## Troubleshooting

### Common Issues

**Import errors (`ModuleNotFoundError`)**
```bash
# Install dependencies
pip install -r pipeline/requirements.txt
```

**Validation errors**
- Check that input transcript is not empty
- Verify JSON schemas exist in `schemas/` directory
- Ensure artifact structure matches schema

**LLM generation fails**
- Verify `OPENAI_API_KEY` is set correctly
- Check API key has sufficient credits
- Review retry logs for specific errors
- Reduce `--openai-model` to `gpt-4o-mini` for cost

**Progress not showing**
- Progress tracking is automatic
- Ensure you're not redirecting stdout
- Check for errors in earlier stages

### Debug Mode

For detailed output:
```bash
# Python's verbose mode
python -v pipeline/run_pipeline.py

# Check specific module
python -c "from pipeline.schema_validator import SchemaValidator; print('OK')"
```

---

## Performance

**Typical execution times** (without LLM):
- Thread generation: ~0.1s (fallback mode)
- Artifact generation: ~0.05s (template-based)
- Validation: ~0.05s
- **Total: ~0.2s**

**With LLM** (depends on API latency):
- Thread generation: ~2-5s
- Artifact generation: ~3-8s
- **Total: ~5-13s**

**Optimizations:**
- Schema validation uses caching
- Retry logic avoids unnecessary delays
- Progress tracking has minimal overhead

---

## Code Quality & Metrics

**Recent improvements (Feb 2026):**
- 67% reduction in main pipeline file (895 → 292 lines)
- 98% reduction in validation code (342 → 8 lines)
- 91% reduction in hardcoded content (350 → 30 lines)
- Added 733 lines of reusable infrastructure
- All changes backward compatible
- 100% CI test pass rate

**Code standards:**
- Type hints for all functions
- Docstrings for public APIs
- JSON Schema for data validation
- Comprehensive error handling

---

## Contributing

When adding new features:

1. **Add schemas first** - Define JSON schemas before implementation
2. **Use existing utilities** - Leverage retry logic, progress tracking, etc.
3. **Follow preset pattern** - New presets go in `content_templates.py`
4. **Validate everything** - Use `SchemaValidator` for all outputs
5. **Add progress tracking** - Use `ProgressTracker` for multi-step operations
6. **Handle errors gracefully** - Use retry logic for external calls

---

## See Also

- [Implementation Summary](../IMPLEMENTATION_SUMMARY.md) - Detailed changes and improvements
- [Verification Checklist](../VERIFICATION_CHECKLIST.md) - Testing guide
- [Test Results](../TEST_RESULTS.md) - Complete test report
- [Main README](../README.md) - Project overview
- [Backend README](../backend/README.md) - API documentation
