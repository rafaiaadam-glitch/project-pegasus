#!/usr/bin/env python3
"""Minimal pipeline runner for schema-validated artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

# Add parent directory to path to allow imports without PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.schema_validator import SchemaValidator
from pipeline.thread_continuity import (
    DEFAULT_CONTINUITY_THRESHOLD,
    continuity_gate_passes,
    score_thread_continuity,
)


ARTIFACT_SCHEMA_DIR = Path("schemas/artifacts")
THREAD_SCHEMA_DIR = Path("schemas")
VERSION = "0.2"


@dataclass(frozen=True)
class PipelineContext:
    course_id: str
    lecture_id: str
    preset_id: str
    generated_at: str
    thread_refs: List[str]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()



def _validate(payload: Dict[str, Any], schema_name: str, base_dir: Path) -> None:
    """Validate payload against JSON schema using jsonschema library."""
    validator = SchemaValidator(base_dir)
    validator.validate(payload, schema_name)



def _base_artifact(context: PipelineContext, artifact_type: str) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "courseId": context.course_id,
        "lectureId": context.lecture_id,
        "presetId": context.preset_id,
        "artifactType": artifact_type,
        "generatedAt": context.generated_at,
        "version": VERSION,
        "threadRefs": context.thread_refs,
    }


def _summary(context: PipelineContext, transcript: str) -> Dict[str, Any]:
    from pipeline.content_templates import get_summary_template

    data = _base_artifact(context, "summary")
    template = get_summary_template(context.preset_id, context.lecture_id)
    data.update(template)
    return data


def _outline(context: PipelineContext) -> Dict[str, Any]:
    from pipeline.content_templates import get_outline_template

    data = _base_artifact(context, "outline")
    template = get_outline_template(context.preset_id)
    data.update(template)
    return data


def _key_terms(context: PipelineContext) -> Dict[str, Any]:
    from pipeline.content_templates import get_key_terms_template

    data = _base_artifact(context, "key-terms")
    template = get_key_terms_template(context.preset_id, context.thread_refs)
    data.update(template)
    return data


def _flashcards(context: PipelineContext) -> Dict[str, Any]:
    from pipeline.content_templates import get_flashcards_template

    data = _base_artifact(context, "flashcards")
    template = get_flashcards_template(context.preset_id, context.thread_refs)
    data.update(template)
    return data


def _exam_questions(context: PipelineContext) -> Dict[str, Any]:
    from pipeline.content_templates import get_exam_questions_template

    data = _base_artifact(context, "exam-questions")
    template = get_exam_questions_template(context.preset_id, context.thread_refs)
    data.update(template)
    return data


def _generate_thread_records(
    context: PipelineContext,
    transcript: str,
    llm_provider: str = "openai",
    llm_model: str | None = None,
    generate_artifacts: bool = False,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    from pipeline.thread_engine import generate_thread_records

    return generate_thread_records(
        course_id=context.course_id,
        lecture_id=context.lecture_id,
        transcript=transcript,
        generated_at=context.generated_at,
        storage_dir=Path("storage"),
        llm_provider=llm_provider,
        llm_model=llm_model,
        preset_id=context.preset_id,
        generate_artifacts=generate_artifacts,
    )


def _strip_nulls(items: list, allowed_keys: set | None = None) -> list:
    """Strip null values and unexpected keys from a list of dicts (LLM output sanitisation)."""
    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            continue
        d = {k: v for k, v in item.items() if v is not None and (allowed_keys is None or k in allowed_keys)}
        if d:
            cleaned.append(d)
    return cleaned


def _wrap_thread_engine_artifacts(
    raw: Dict[str, Any],
    context: PipelineContext,
) -> Dict[str, Dict[str, Any]]:
    """Wrap raw artifact data from the Thread Engine LLM call into schema-conformant envelopes."""
    artifacts: Dict[str, Dict[str, Any]] = {}

    # summary → needs overview + sections[{title, bullets}]
    if "summary" in raw:
        s = raw["summary"]
        base = _base_artifact(context, "summary")
        base["overview"] = s.get("overview", "")
        base["sections"] = _strip_nulls(s.get("sections", []), {"title", "bullets"})
        artifacts["summary"] = base

    # outline → needs outline[{title, points?, children?}]
    if "outline" in raw:
        base = _base_artifact(context, "outline")
        outline_data = raw["outline"] if isinstance(raw["outline"], list) else raw["outline"].get("sections", raw["outline"])
        base["outline"] = _strip_nulls(outline_data, {"title", "points", "children"})
        artifacts["outline"] = base

    # key-terms → needs terms[{term, definition}]
    if "key_terms" in raw:
        base = _base_artifact(context, "key-terms")
        terms = raw["key_terms"] if isinstance(raw["key_terms"], list) else raw["key_terms"].get("terms", [])
        base["terms"] = _strip_nulls(terms, {"term", "definition", "example", "threadRef"})
        artifacts["key-terms"] = base

    # flashcards → needs cards[{front, back}]
    if "flashcards" in raw:
        base = _base_artifact(context, "flashcards")
        cards = raw["flashcards"] if isinstance(raw["flashcards"], list) else raw["flashcards"].get("cards", [])
        base["cards"] = _strip_nulls(cards, {"front", "back", "difficulty", "tags", "threadRef"})
        artifacts["flashcards"] = base

    # exam-questions → needs questions[{prompt, type, answer}]
    if "exam_questions" in raw:
        base = _base_artifact(context, "exam-questions")
        questions = raw["exam_questions"] if isinstance(raw["exam_questions"], list) else raw["exam_questions"].get("questions", [])
        base["questions"] = _strip_nulls(questions, {"prompt", "type", "answer", "choices", "correctChoiceIndex", "threadRef"})
        artifacts["exam-questions"] = base

    return artifacts


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def run_pipeline(
    transcript: str,
    context: PipelineContext,
    output_dir: Path,
    use_llm: bool = False,
    openai_model: str = "gpt-4o-mini",  # Fallback for legacy OpenAI calls
    llm_provider: str = "openai",  # Default to OpenAI
    llm_model: str | None = None,
    progress_tracker=None,
    continuity_threshold: float | None = None,
) -> None:
    # STEP 1: Generate threads AND artifacts in a single LLM call
    if progress_tracker:
        progress_tracker.start_step("thread_generation")

    threads, thread_occurrences, thread_updates = _generate_thread_records(
        context,
        transcript,
        llm_provider=llm_provider,
        llm_model=llm_model or openai_model,
        generate_artifacts=use_llm,
    )

    if progress_tracker:
        progress_tracker.complete_step("thread_generation")

    # STEP 2: Extract real thread IDs from generated threads (take first 3 if available)
    thread_ids = [t["id"] for t in threads[:3]] if threads else []

    # STEP 3: Update context with REAL thread refs
    updated_context = PipelineContext(
        course_id=context.course_id,
        lecture_id=context.lecture_id,
        preset_id=context.preset_id,
        generated_at=context.generated_at,
        thread_refs=thread_ids,  # Real UUIDs from actual threads
    )

    continuity_metrics = score_thread_continuity(
        threads=threads,
        occurrences=thread_occurrences,
        updates=thread_updates,
    )
    continuity_payload = {
        "metrics": continuity_metrics,
        "threshold": continuity_threshold,
        "passed": continuity_gate_passes(
            continuity_metrics,
            threshold=continuity_threshold
            if continuity_threshold is not None
            else DEFAULT_CONTINUITY_THRESHOLD,
        ),
    }

    # STEP 4: Build artifacts from Thread Engine output or fallback templates
    if progress_tracker:
        progress_tracker.start_step("artifact_generation")

    if use_llm:
        from pipeline.thread_engine import get_last_artifacts

        raw_artifacts = get_last_artifacts() or {}
        artifacts = _wrap_thread_engine_artifacts(raw_artifacts, updated_context)
    else:
        artifacts = {
            "summary": _summary(updated_context, transcript),
            "outline": _outline(updated_context),
            "key-terms": _key_terms(updated_context),
            "flashcards": _flashcards(updated_context),
            "exam-questions": _exam_questions(updated_context),
        }

    if progress_tracker:
        progress_tracker.complete_step("artifact_generation")

    # STEP 5: Validate and save everything
    if progress_tracker:
        progress_tracker.start_step("validation_and_save")

    for artifact_type, payload in artifacts.items():
        schema_name = f"{artifact_type}.schema.json"
        _validate(payload, schema_name, ARTIFACT_SCHEMA_DIR)
        output_path = output_dir / updated_context.lecture_id / f"{artifact_type}.json"
        _write_json(output_path, payload)

    for thread in threads:
        _validate(thread, "thread.schema.json", THREAD_SCHEMA_DIR)
    _write_json(output_dir / updated_context.lecture_id / "threads.json", {"threads": threads})

    for occurrence in thread_occurrences:
        _validate(occurrence, "thread-occurrence.schema.json", THREAD_SCHEMA_DIR)
    _write_json(
        output_dir / updated_context.lecture_id / "thread-occurrences.json",
        {"occurrences": thread_occurrences},
    )

    for update in thread_updates:
        _validate(update, "thread-update.schema.json", THREAD_SCHEMA_DIR)
    _write_json(
        output_dir / updated_context.lecture_id / "thread-updates.json",
        {"updates": thread_updates},
    )
    _write_json(
        output_dir / updated_context.lecture_id / "thread-continuity.json",
        continuity_payload,
    )

    if continuity_threshold is not None and not continuity_payload["passed"]:
        score = continuity_metrics["score"]
        raise ValueError(
            f"Thread continuity gate failed: score={score} threshold={continuity_threshold}"
        )

    if progress_tracker:
        progress_tracker.complete_step("validation_and_save")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Pegasus artifact pipeline.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("pipeline/inputs/sample-transcript.txt"),
        help="Path to lecture transcript text.",
    )
    parser.add_argument("--course-id", default="course-001")
    parser.add_argument("--lecture-id", default="lecture-001")
    parser.add_argument("--preset-id", default="exam-mode")
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Generate artifacts using configured LLM provider.",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-4o-mini",
        help="Deprecated alias for --llm-model when using OpenAI.",
    )
    parser.add_argument(
        "--llm-provider",
        default=os.getenv("PLC_LLM_PROVIDER", "openai"),
        choices=["openai"],
        help="LLM provider for generation.",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="Model name for selected LLM provider.",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export artifacts to Markdown, PDF, and Anki CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("pipeline/output"),
        help="Output directory for artifacts.",
    )
    parser.add_argument(
        "--progress-log-file",
        type=Path,
        default=None,
        help="Optional file path to append progress logs and final summary.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable console progress output (use with --progress-log-file for persisted logs).",
    )
    parser.add_argument(
        "--continuity-threshold",
        type=float,
        default=None,
        help=(
            "Optional minimum thread continuity score (0-1). "
            "If set, pipeline exits with an error when score is below threshold."
        ),
    )
    return parser.parse_args()


def main() -> None:
    from pipeline.progress_tracker import ProgressTracker

    args = _parse_args()
    if args.input.suffix == ".json":
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        transcript = payload.get("text", "")
        if not transcript:
            raise ValueError("Transcript JSON missing 'text' field.")
    else:
        transcript = args.input.read_text(encoding="utf-8")

    context = PipelineContext(
        course_id=args.course_id,
        lecture_id=args.lecture_id,
        preset_id=args.preset_id,
        generated_at=_now_iso(),
        thread_refs=[],  # Start empty, populated in run_pipeline
    )

    tracker = ProgressTracker(
        total_steps=3,
        verbose=not args.quiet,
        log_file=str(args.progress_log_file) if args.progress_log_file else None,
    )
    run_pipeline(
        transcript,
        context,
        args.output_dir,
        use_llm=args.use_llm,
        openai_model=args.openai_model,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        progress_tracker=tracker,
        continuity_threshold=args.continuity_threshold,
    )
    tracker.print_summary()
    if not args.quiet:
        print(f"Artifacts written to {args.output_dir / args.lecture_id}")

    if args.export:
        from pipeline.export_artifacts import export_artifacts

        export_artifacts(
            lecture_id=args.lecture_id,
            artifact_dir=args.output_dir / args.lecture_id,
            export_dir=Path("storage") / "exports" / args.lecture_id,
        )
        if not args.quiet:
            print(f"Exports written to {Path('storage') / 'exports' / args.lecture_id}")


if __name__ == "__main__":
    main()
