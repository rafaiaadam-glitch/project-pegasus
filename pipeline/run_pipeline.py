#!/usr/bin/env python3
"""Minimal pipeline runner for schema-validated artifacts."""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


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


def _load_schema(name: str, base_dir: Path) -> Dict[str, Any]:
    schema_path = base_dir / name
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _assert(condition: bool, message: str, errors: List[str]) -> None:
    if not condition:
        errors.append(message)


def _assert_required(payload: Dict[str, Any], fields: Sequence[str], errors: List[str]) -> None:
    for field in fields:
        _assert(field in payload, f"missing required field '{field}'", errors)


def _assert_non_empty_string(value: Any, label: str, errors: List[str]) -> None:
    _assert(isinstance(value, str), f"'{label}' must be a string", errors)
    if isinstance(value, str):
        _assert(value.strip() != "", f"'{label}' must be non-empty", errors)


def _assert_list(value: Any, label: str, errors: List[str]) -> None:
    _assert(isinstance(value, list), f"'{label}' must be a list", errors)


def _validate_common(payload: Dict[str, Any], artifact_type: str, errors: List[str]) -> None:
    _assert_required(
        payload,
        ["id", "courseId", "lectureId", "presetId", "artifactType", "generatedAt", "version"],
        errors,
    )
    _assert(payload.get("artifactType") == artifact_type, "artifactType mismatch", errors)
    for field in ("id", "courseId", "lectureId", "presetId", "artifactType", "generatedAt", "version"):
        if field in payload:
            _assert_non_empty_string(payload[field], field, errors)
    if "threadRefs" in payload:
        _assert_list(payload["threadRefs"], "threadRefs", errors)
        if isinstance(payload["threadRefs"], list):
            for idx, value in enumerate(payload["threadRefs"]):
                _assert_non_empty_string(value, f"threadRefs[{idx}]", errors)


def _validate_summary(payload: Dict[str, Any], errors: List[str]) -> None:
    _assert_required(payload, ["overview", "sections"], errors)
    if "overview" in payload:
        _assert_non_empty_string(payload["overview"], "overview", errors)
    if "sections" in payload:
        _assert_list(payload["sections"], "sections", errors)
        if isinstance(payload["sections"], list):
            _assert(len(payload["sections"]) > 0, "'sections' must not be empty", errors)
            for idx, section in enumerate(payload["sections"]):
                _assert(isinstance(section, dict), f"sections[{idx}] must be an object", errors)
                if isinstance(section, dict):
                    _assert_required(section, ["title", "bullets"], errors)
                    if "title" in section:
                        _assert_non_empty_string(section["title"], f"sections[{idx}].title", errors)
                    if "bullets" in section:
                        _assert_list(section["bullets"], f"sections[{idx}].bullets", errors)
                        if isinstance(section["bullets"], list):
                            _assert(
                                len(section["bullets"]) > 0,
                                f"sections[{idx}].bullets must not be empty",
                                errors,
                            )
                            for bullet_index, bullet in enumerate(section["bullets"]):
                                _assert_non_empty_string(
                                    bullet,
                                    f"sections[{idx}].bullets[{bullet_index}]",
                                    errors,
                                )


def _validate_outline(payload: Dict[str, Any], errors: List[str]) -> None:
    _assert_required(payload, ["outline"], errors)
    if "outline" in payload:
        _assert_list(payload["outline"], "outline", errors)
        if isinstance(payload["outline"], list):
            _assert(len(payload["outline"]) > 0, "'outline' must not be empty", errors)
            for idx, node in enumerate(payload["outline"]):
                _validate_outline_node(node, f"outline[{idx}]", errors)


def _validate_outline_node(node: Any, label: str, errors: List[str]) -> None:
    _assert(isinstance(node, dict), f"{label} must be an object", errors)
    if not isinstance(node, dict):
        return
    _assert_required(node, ["title"], errors)
    if "title" in node:
        _assert_non_empty_string(node["title"], f"{label}.title", errors)
    if "points" in node:
        _assert_list(node["points"], f"{label}.points", errors)
        if isinstance(node["points"], list):
            for idx, point in enumerate(node["points"]):
                _assert_non_empty_string(point, f"{label}.points[{idx}]", errors)
    if "children" in node:
        _assert_list(node["children"], f"{label}.children", errors)
        if isinstance(node["children"], list):
            for idx, child in enumerate(node["children"]):
                _validate_outline_node(child, f"{label}.children[{idx}]", errors)


def _validate_key_terms(payload: Dict[str, Any], errors: List[str]) -> None:
    _assert_required(payload, ["terms"], errors)
    if "terms" in payload:
        _assert_list(payload["terms"], "terms", errors)
        if isinstance(payload["terms"], list):
            _assert(len(payload["terms"]) > 0, "'terms' must not be empty", errors)
            for idx, term in enumerate(payload["terms"]):
                _assert(isinstance(term, dict), f"terms[{idx}] must be an object", errors)
                if isinstance(term, dict):
                    _assert_required(term, ["term", "definition"], errors)
                    if "term" in term:
                        _assert_non_empty_string(term["term"], f"terms[{idx}].term", errors)
                    if "definition" in term:
                        _assert_non_empty_string(
                            term["definition"], f"terms[{idx}].definition", errors
                        )
                    if "example" in term:
                        _assert_non_empty_string(term["example"], f"terms[{idx}].example", errors)
                    if "threadRef" in term:
                        _assert_non_empty_string(term["threadRef"], f"terms[{idx}].threadRef", errors)


def _validate_flashcards(payload: Dict[str, Any], errors: List[str]) -> None:
    _assert_required(payload, ["cards"], errors)
    if "cards" in payload:
        _assert_list(payload["cards"], "cards", errors)
        if isinstance(payload["cards"], list):
            _assert(len(payload["cards"]) > 0, "'cards' must not be empty", errors)
            for idx, card in enumerate(payload["cards"]):
                _assert(isinstance(card, dict), f"cards[{idx}] must be an object", errors)
                if isinstance(card, dict):
                    _assert_required(card, ["front", "back"], errors)
                    if "front" in card:
                        _assert_non_empty_string(card["front"], f"cards[{idx}].front", errors)
                    if "back" in card:
                        _assert_non_empty_string(card["back"], f"cards[{idx}].back", errors)
                    if "difficulty" in card:
                        _assert(
                            card["difficulty"] in {"easy", "medium", "hard"},
                            f"cards[{idx}].difficulty must be easy|medium|hard",
                            errors,
                        )
                    if "tags" in card:
                        _assert_list(card["tags"], f"cards[{idx}].tags", errors)
                        if isinstance(card["tags"], list):
                            for tag_index, tag in enumerate(card["tags"]):
                                _assert_non_empty_string(
                                    tag, f"cards[{idx}].tags[{tag_index}]", errors
                                )
                    if "threadRef" in card:
                        _assert_non_empty_string(
                            card["threadRef"], f"cards[{idx}].threadRef", errors
                        )


def _validate_exam_questions(payload: Dict[str, Any], errors: List[str]) -> None:
    _assert_required(payload, ["questions"], errors)
    if "questions" in payload:
        _assert_list(payload["questions"], "questions", errors)
        if isinstance(payload["questions"], list):
            _assert(len(payload["questions"]) > 0, "'questions' must not be empty", errors)
            for idx, question in enumerate(payload["questions"]):
                _assert(isinstance(question, dict), f"questions[{idx}] must be an object", errors)
                if isinstance(question, dict):
                    _assert_required(question, ["prompt", "type", "answer"], errors)
                    if "prompt" in question:
                        _assert_non_empty_string(
                            question["prompt"], f"questions[{idx}].prompt", errors
                        )
                    if "type" in question:
                        _assert(
                            question["type"]
                            in {"multiple-choice", "short-answer", "essay", "true-false"},
                            f"questions[{idx}].type must be a supported value",
                            errors,
                        )
                    if "answer" in question:
                        _assert_non_empty_string(
                            question["answer"], f"questions[{idx}].answer", errors
                        )
                    if "choices" in question:
                        _assert_list(question["choices"], f"questions[{idx}].choices", errors)
                        if isinstance(question["choices"], list):
                            for choice_index, choice in enumerate(question["choices"]):
                                _assert_non_empty_string(
                                    choice,
                                    f"questions[{idx}].choices[{choice_index}]",
                                    errors,
                                )
                    if "correctChoiceIndex" in question:
                        _assert(
                            isinstance(question["correctChoiceIndex"], int),
                            f"questions[{idx}].correctChoiceIndex must be an integer",
                            errors,
                        )
                    if "threadRef" in question:
                        _assert_non_empty_string(
                            question["threadRef"], f"questions[{idx}].threadRef", errors
                        )


def _validate_thread(payload: Dict[str, Any], errors: List[str]) -> None:
    _assert_required(
        payload,
        ["id", "courseId", "title", "summary", "status", "complexityLevel", "lectureRefs"],
        errors,
    )
    if "id" in payload:
        _assert_non_empty_string(payload["id"], "id", errors)
    if "courseId" in payload:
        _assert_non_empty_string(payload["courseId"], "courseId", errors)
    if "title" in payload:
        _assert_non_empty_string(payload["title"], "title", errors)
    if "summary" in payload:
        _assert_non_empty_string(payload["summary"], "summary", errors)
    if "status" in payload:
        _assert(
            payload["status"] in {"foundational", "advanced"},
            "status must be foundational|advanced",
            errors,
        )
    if "complexityLevel" in payload:
        _assert(
            isinstance(payload["complexityLevel"], int),
            "complexityLevel must be an integer",
            errors,
        )
        if isinstance(payload["complexityLevel"], int):
            _assert(
                1 <= payload["complexityLevel"] <= 5,
                "complexityLevel must be between 1 and 5",
                errors,
            )
    if "lectureRefs" in payload:
        _assert_list(payload["lectureRefs"], "lectureRefs", errors)
        if isinstance(payload["lectureRefs"], list):
            _assert(len(payload["lectureRefs"]) > 0, "lectureRefs must not be empty", errors)
            for idx, lecture_ref in enumerate(payload["lectureRefs"]):
                _assert_non_empty_string(
                    lecture_ref, f"lectureRefs[{idx}]", errors
                )
    if "evolutionNotes" in payload:
        _assert_list(payload["evolutionNotes"], "evolutionNotes", errors)
        if isinstance(payload["evolutionNotes"], list):
            for idx, note in enumerate(payload["evolutionNotes"]):
                _assert(isinstance(note, dict), f"evolutionNotes[{idx}] must be an object", errors)
                if isinstance(note, dict):
                    _assert_required(note, ["lectureId", "changeType", "note"], errors)
                    if "lectureId" in note:
                        _assert_non_empty_string(
                            note["lectureId"], f"evolutionNotes[{idx}].lectureId", errors
                        )
                    if "changeType" in note:
                        _assert(
                            note["changeType"]
                            in {"refinement", "contradiction", "complexity"},
                            f"evolutionNotes[{idx}].changeType must be a supported value",
                            errors,
                        )
                    if "note" in note:
                        _assert_non_empty_string(
                            note["note"], f"evolutionNotes[{idx}].note", errors
                        )


def _validate_thread_occurrence(payload: Dict[str, Any], errors: List[str]) -> None:
    _assert_required(
        payload,
        ["id", "threadId", "courseId", "lectureId", "artifactId", "evidence", "confidence", "capturedAt"],
        errors,
    )
    for field in ("id", "threadId", "courseId", "lectureId", "artifactId", "evidence", "capturedAt"):
        if field in payload:
            _assert_non_empty_string(payload[field], field, errors)
    if "confidence" in payload:
        _assert(
            isinstance(payload["confidence"], (int, float)),
            "confidence must be a number",
            errors,
        )
        if isinstance(payload["confidence"], (int, float)):
            _assert(
                0 <= payload["confidence"] <= 1,
                "confidence must be between 0 and 1",
                errors,
            )


def _validate_thread_update(payload: Dict[str, Any], errors: List[str]) -> None:
    _assert_required(
        payload,
        ["id", "threadId", "courseId", "lectureId", "changeType", "summary", "capturedAt"],
        errors,
    )
    for field in ("id", "threadId", "courseId", "lectureId", "summary", "capturedAt"):
        if field in payload:
            _assert_non_empty_string(payload[field], field, errors)
    if "changeType" in payload:
        _assert(
            payload["changeType"] in {"refinement", "contradiction", "complexity"},
            "changeType must be a supported value",
            errors,
        )
    if "details" in payload:
        _assert_list(payload["details"], "details", errors)
        if isinstance(payload["details"], list):
            for idx, detail in enumerate(payload["details"]):
                _assert_non_empty_string(detail, f"details[{idx}]", errors)


def _validate(payload: Dict[str, Any], schema_name: str, base_dir: Path) -> None:
    _load_schema(schema_name, base_dir)
    errors: List[str] = []
    if schema_name == "summary.schema.json":
        _validate_common(payload, "summary", errors)
        _validate_summary(payload, errors)
    elif schema_name == "outline.schema.json":
        _validate_common(payload, "outline", errors)
        _validate_outline(payload, errors)
    elif schema_name == "key-terms.schema.json":
        _validate_common(payload, "key-terms", errors)
        _validate_key_terms(payload, errors)
    elif schema_name == "flashcards.schema.json":
        _validate_common(payload, "flashcards", errors)
        _validate_flashcards(payload, errors)
    elif schema_name == "exam-questions.schema.json":
        _validate_common(payload, "exam-questions", errors)
        _validate_exam_questions(payload, errors)
    elif schema_name == "thread.schema.json":
        _validate_thread(payload, errors)
    elif schema_name == "thread-occurrence.schema.json":
        _validate_thread_occurrence(payload, errors)
    elif schema_name == "thread-update.schema.json":
        _validate_thread_update(payload, errors)
    else:
        errors.append(f"unsupported schema '{schema_name}'")
    if errors:
        message_lines = [f"Schema validation failed ({schema_name}):"]
        message_lines.extend(f"- {error}" for error in errors)
        raise ValueError("\n".join(message_lines))


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
    data = _base_artifact(context, "summary")
    preset = context.preset_id.lower()
    if preset in {"beginner-mode", "beginner"}:
        overview = "Plain-language recap focused on core intuition and examples."
        sections = [
            {
                "title": "Big idea",
                "bullets": [
                    "Neurons send quick electrical messages called action potentials.",
                    "Signals move faster when axons are wrapped in myelin.",
                ],
            },
            {
                "title": "Why it matters",
                "bullets": [
                    "Faster signals mean quicker reactions and learning.",
                    "Synapses can be strengthened with repeated practice.",
                ],
            },
        ]
    elif preset in {"neurodivergent-friendly", "neurodivergent-friendly-mode"}:
        overview = "Short, low-clutter recap with quick checkpoints."
        sections = [
            {
                "title": "Key checkpoints",
                "bullets": [
                    "Action potential = quick electrical spike.",
                    "Sodium in, potassium out.",
                    "Myelin speeds signals.",
                ],
            },
            {
                "title": "Remember",
                "bullets": [
                    "Synapses can be excitatory or inhibitory.",
                    "Practice strengthens synapses.",
                ],
            },
        ]
    elif preset in {"research-mode", "research"}:
        overview = "Claim-focused summary with evidence placeholders."
        sections = [
            {
                "title": "Claims",
                "bullets": [
                    "Action potentials depend on ion channel dynamics. [evidence]",
                    "Myelination increases conduction velocity. [evidence]",
                ],
            },
            {
                "title": "Open questions",
                "bullets": [
                    "What experimental data best quantifies synaptic strengthening?",
                    "How do inhibitory synapses affect network stability?",
                ],
            },
        ]
    elif preset in {"concept-map-mode", "concept-map"}:
        overview = "Relationship-first summary emphasizing connections."
        sections = [
            {
                "title": "Core relationships",
                "bullets": [
                    "Ion channels → membrane voltage → action potential.",
                    "Myelination → saltatory conduction → faster signaling.",
                ],
            },
            {
                "title": "Cross-lecture hooks",
                "bullets": [
                    "Synaptic strengthening links to memory and learning.",
                    "Excitation/inhibition balance ties to network behavior.",
                ],
            },
        ]
    else:
        overview = (
            f"Preset '{context.preset_id}' summary of lecture {context.lecture_id}."
        )
        sections = [
            {
                "title": "Signal flow essentials",
                "bullets": [
                    "Neurons communicate via action potentials and synapses.",
                    "Ion channels drive depolarization and repolarization.",
                ],
            },
            {
                "title": "Continuity hooks",
                "bullets": [
                    "Myelination increases speed through saltatory conduction.",
                    "Repeated stimulation strengthens synapses for later lectures.",
                ],
            },
        ]
    data.update(
        {
            "overview": overview,
            "sections": sections,
        }
    )
    return data


def _outline(context: PipelineContext) -> Dict[str, Any]:
    data = _base_artifact(context, "outline")
    preset = context.preset_id.lower()
    if preset in {"concept-map-mode", "concept-map"}:
        outline = [
            {
                "title": "Neuron signaling map",
                "points": ["Action potentials", "Synapses", "Ion channels"],
                "children": [
                    {
                        "title": "Speed factors",
                        "points": ["Myelination", "Saltatory conduction"],
                    },
                    {
                        "title": "Adaptation",
                        "points": ["Synaptic strengthening", "Learning prep"],
                    },
                ],
            }
        ]
    elif preset in {"exam-mode", "exam"}:
        outline = [
            {
                "title": "Exam essentials",
                "points": [
                    "Define resting potential, depolarization, repolarization",
                    "Explain sodium vs potassium channel roles",
                    "Contrast saltatory vs continuous conduction",
                ],
            },
            {
                "title": "Common exam angles",
                "points": [
                    "Explain synaptic excitation vs inhibition",
                    "Describe how myelination changes speed",
                ],
            },
        ]
    else:
        outline = [
            {
                "title": "Action potentials",
                "points": [
                    "Resting potential and threshold",
                    "Depolarization via sodium influx",
                    "Repolarization via potassium efflux",
                ],
            },
            {
                "title": "Signal transmission",
                "points": [
                    "Synaptic excitation vs inhibition",
                    "Myelination and conduction speed",
                ],
                "children": [
                    {
                        "title": "Saltatory vs continuous conduction",
                        "points": [
                            "Saltatory conduction jumps between nodes",
                            "Continuous conduction is slower in unmyelinated axons",
                        ],
                    }
                ],
            },
        ]
    data.update(
        {"outline": outline}
    )
    return data


def _key_terms(context: PipelineContext) -> Dict[str, Any]:
    data = _base_artifact(context, "key-terms")
    preset = context.preset_id.lower()
    if preset in {"beginner-mode", "beginner"}:
        terms = [
            {
                "term": "Action potential",
                "definition": "A quick electrical signal sent by a neuron.",
                "threadRef": context.thread_refs[0],
            },
            {
                "term": "Myelin",
                "definition": "A fatty coating that helps signals travel faster.",
            },
        ]
    elif preset in {"research-mode", "research"}:
        terms = [
            {
                "term": "Depolarization",
                "definition": "Shift toward positive membrane voltage. [evidence]",
                "threadRef": context.thread_refs[1],
            },
            {
                "term": "Synaptic plasticity",
                "definition": "Change in synaptic strength over time. [evidence]",
            },
        ]
    else:
        terms = [
            {
                "term": "Resting potential",
                "definition": "Baseline voltage across a neuron before firing.",
                "threadRef": context.thread_refs[0],
            },
            {
                "term": "Depolarization",
                "definition": "Rapid rise in membrane voltage driven by sodium influx.",
                "threadRef": context.thread_refs[1],
            },
            {
                "term": "Saltatory conduction",
                "definition": "Signal propagation that jumps between myelinated nodes.",
            },
        ]
    data.update(
        {"terms": terms}
    )
    return data


def _flashcards(context: PipelineContext) -> Dict[str, Any]:
    data = _base_artifact(context, "flashcards")
    preset = context.preset_id.lower()
    if preset in {"exam-mode", "exam"}:
        cards = [
            {
                "front": "Define depolarization.",
                "back": "Rapid rise in membrane voltage from sodium influx.",
                "difficulty": "easy",
                "tags": ["definitions", "exam"],
                "threadRef": context.thread_refs[1],
            },
            {
                "front": "Compare saltatory vs continuous conduction.",
                "back": "Saltatory jumps between myelinated nodes; continuous is slower.",
                "difficulty": "medium",
                "tags": ["comparisons", "exam"],
            },
        ]
    elif preset in {"neurodivergent-friendly", "neurodivergent-friendly-mode"}:
        cards = [
            {
                "front": "Action potential = ?",
                "back": "A quick electrical spike in a neuron.",
                "difficulty": "easy",
                "tags": ["quick-check"],
            },
            {
                "front": "Myelin helps because?",
                "back": "It speeds up the signal.",
                "difficulty": "easy",
                "tags": ["quick-check"],
            },
        ]
    else:
        cards = [
            {
                "front": "What triggers depolarization in a neuron?",
                "back": "Opening of sodium channels and sodium influx.",
                "difficulty": "easy",
                "tags": ["action-potentials"],
                "threadRef": context.thread_refs[1],
            },
            {
                "front": "Why does myelination matter?",
                "back": "It enables saltatory conduction, increasing speed.",
                "difficulty": "medium",
                "tags": ["conduction"],
            },
        ]
    data.update(
        {"cards": cards}
    )
    return data


def _exam_questions(context: PipelineContext) -> Dict[str, Any]:
    data = _base_artifact(context, "exam-questions")
    preset = context.preset_id.lower()
    if preset in {"research-mode", "research"}:
        questions = [
            {
                "prompt": "Summarize evidence for myelination affecting conduction velocity.",
                "type": "short-answer",
                "answer": "Summarize cited data or experiments. [evidence]",
            },
            {
                "prompt": "What competing hypotheses explain synaptic strengthening?",
                "type": "essay",
                "answer": "List and contrast candidate mechanisms. [evidence]",
            },
        ]
    elif preset in {"exam-mode", "exam"}:
        questions = [
            {
                "prompt": "Which ion movement is most associated with depolarization?",
                "type": "multiple-choice",
                "choices": [
                    "Sodium influx",
                    "Potassium influx",
                    "Chloride efflux",
                    "Calcium efflux",
                ],
                "correctChoiceIndex": 0,
                "answer": "Sodium influx.",
                "threadRef": context.thread_refs[1],
            },
            {
                "prompt": "Explain saltatory conduction in one paragraph.",
                "type": "essay",
                "answer": (
                    "Saltatory conduction describes action potentials that jump between "
                    "nodes of Ranvier in myelinated axons, which speeds signal "
                    "transmission and reduces energy cost."
                ),
            },
        ]
    else:
        questions = [
            {
                "prompt": "Which ion movement is most associated with depolarization?",
                "type": "multiple-choice",
                "choices": [
                    "Sodium influx",
                    "Potassium influx",
                    "Chloride efflux",
                    "Calcium efflux",
                ],
                "correctChoiceIndex": 0,
                "answer": "Sodium influx.",
                "threadRef": context.thread_refs[1],
            },
            {
                "prompt": "Explain saltatory conduction in one paragraph.",
                "type": "essay",
                "answer": (
                    "Saltatory conduction describes action potentials that jump between "
                    "nodes of Ranvier in myelinated axons, which speeds signal "
                    "transmission and reduces energy cost."
                ),
            },
        ]
    data.update(
        {"questions": questions}
    )
    return data


def _generate_thread_records(
    context: PipelineContext, transcript: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    from pipeline.thread_engine import generate_thread_records

    return generate_thread_records(
        course_id=context.course_id,
        lecture_id=context.lecture_id,
        transcript=transcript,
        generated_at=context.generated_at,
        storage_dir=Path("storage"),
    )


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
    openai_model: str = "gpt-4o-mini",
) -> None:
    if use_llm:
        from pipeline.llm_generation import generate_artifacts_with_llm

        artifacts = generate_artifacts_with_llm(
            transcript=transcript,
            preset_id=context.preset_id,
            course_id=context.course_id,
            lecture_id=context.lecture_id,
            generated_at=context.generated_at,
            model=openai_model,
        )
    else:
        artifacts = {
            "summary": _summary(context, transcript),
            "outline": _outline(context),
            "key-terms": _key_terms(context),
            "flashcards": _flashcards(context),
            "exam-questions": _exam_questions(context),
        }

    for artifact_type, payload in artifacts.items():
        schema_name = f"{artifact_type}.schema.json"
        _validate(payload, schema_name, ARTIFACT_SCHEMA_DIR)
        output_path = output_dir / context.lecture_id / f"{artifact_type}.json"
        _write_json(output_path, payload)

    artifact_ids = {name: payload["id"] for name, payload in artifacts.items()}
    threads, thread_occurrences, thread_updates = _generate_thread_records(
        context, transcript
    )
    for thread in threads:
        _validate(thread, "thread.schema.json", THREAD_SCHEMA_DIR)
    _write_json(output_dir / context.lecture_id / "threads.json", {"threads": threads})

    for occurrence in thread_occurrences:
        _validate(occurrence, "thread-occurrence.schema.json", THREAD_SCHEMA_DIR)
    _write_json(
        output_dir / context.lecture_id / "thread-occurrences.json",
        {"occurrences": thread_occurrences},
    )

    for update in thread_updates:
        _validate(update, "thread-update.schema.json", THREAD_SCHEMA_DIR)
    _write_json(
        output_dir / context.lecture_id / "thread-updates.json",
        {"updates": thread_updates},
    )


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
        help="Generate artifacts using OpenAI responses.",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-4o-mini",
        help="OpenAI model for LLM-backed generation.",
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
    return parser.parse_args()


def main() -> None:
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
        thread_refs=["thread-neuron-signaling", "thread-ion-channels"],
    )

    run_pipeline(
        transcript,
        context,
        args.output_dir,
        use_llm=args.use_llm,
        openai_model=args.openai_model,
    )
    print(f"Artifacts written to {args.output_dir / args.lecture_id}")

    if args.export:
        from pipeline.export_artifacts import export_artifacts

        export_artifacts(
            lecture_id=args.lecture_id,
            artifact_dir=args.output_dir / args.lecture_id,
            export_dir=Path("storage") / "exports" / args.lecture_id,
        )
        print(f"Exports written to {Path('storage') / 'exports' / args.lecture_id}")


if __name__ == "__main__":
    main()
