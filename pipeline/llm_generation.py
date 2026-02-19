from __future__ import annotations

import importlib.util
import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

if importlib.util.find_spec("vertexai"):
    import vertexai
    from vertexai.generative_models import GenerationConfig, GenerativeModel
else:
    vertexai = None

    class GenerationConfig(dict):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)

    class GenerativeModel:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("vertexai is required for Gemini/Vertex generation")


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _base_artifact(
    artifact_type: str,
    course_id: str,
    lecture_id: str,
    preset_id: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "id": f"artifact-{uuid.uuid4()}",
        "artifactType": artifact_type,
        "courseId": course_id,
        "lectureId": lecture_id,
        "presetId": preset_id,
        "generatedAt": generated_at,
        "version": "0.2",
    }


def _load_preset_config(preset_id: str) -> dict[str, Any] | None:
    from backend.presets import PRESETS

    normalized = preset_id.strip().lower()
    for preset in PRESETS:
        pid = str(preset.get("id", "")).strip().lower()
        kind = str(preset.get("kind", "")).strip().lower()
        if normalized in {pid, kind, pid.removesuffix("-mode"), kind.removesuffix("-mode")}:
            return preset
    return None


def _tone_directive(tone: str) -> str:
    mapping = {
        "formal_academic": "Use formal academic language. Be precise and scholarly.",
        "conversational": "Use plain, everyday language. Explain clearly with examples and analogies.",
        "direct_predictable": "Use short, direct sentences. Prefer numbered steps and predictable formatting.",
        "analytical_precise": "Use precise technical language and emphasize evidence and mechanisms.",
        "dialectical": "Present arguments and counterarguments, and attribute positions to speakers.",
    }
    return mapping.get(tone, "Use clear, structured academic language.")


def _build_generation_prompt(preset_id: str, preset_config: dict[str, Any] | None) -> str:
    generation = (preset_config or {}).get("generation_config", {})
    summary_max_words = generation.get("summary_max_words", 700)
    flashcard_count = generation.get("flashcard_count", 20)
    exam_question_count = generation.get("exam_question_count", 10)
    tone = generation.get("tone", "formal_academic")
    question_types = generation.get("question_types", ["definition", "application"])
    special_instructions = generation.get("special_instructions", [])

    special_lines = "\n".join(f"- {item}" for item in special_instructions) if special_instructions else "- None"

    preset_name = (preset_config or {}).get("name", preset_id)

    return (
        "You are Pegasus Lecture Copilot. Return ONLY valid JSON with no markdown.\n"
        f"Preset: {preset_name} ({preset_id})\n"
        f"Tone directive: {_tone_directive(str(tone))}\n"
        f"Summary max words: {summary_max_words}\n"
        f"Flashcard count target: {flashcard_count}\n"
        f"Exam question count target: {exam_question_count}\n"
        f"Question types: {', '.join(map(str, question_types))}\n"
        "Special instructions:\n"
        f"{special_lines}\n\n"
        "Required top-level JSON keys: summary, outline, key_terms, flashcards, exam_questions.\n"
        "Each artifact object should be content-only (metadata added later), but compatible with artifactType mapping.\n"
        "Expected structures:\n"
        "- summary: {overview: string, sections: [{title: string, bullets: [string]}]}\n"
        "- outline: {outline: [{title: string, points: [string], children: [object]}]}\n"
        "- key_terms: {terms: [{term: string, definition: string}]}\n"
        "- flashcards: {cards: [{front: string, back: string}]}\n"
        "- exam_questions: {questions: [{prompt: string, type: string, answer: string, choices: [string], correctChoiceIndex: number|null}]}\n"
    )


def _request_openai(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI generation")

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_openai_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                return content["text"]

    raise ValueError("OpenAI response did not contain output text")


def generate_artifacts_with_llm(
    transcript: str,
    preset_id: str,
    course_id: str,
    lecture_id: str,
    generated_at: str | None = None,
    model: str = "gemini-3-pro-preview",
    thread_refs: list[str] | None = None,
    provider: str = "gemini",
) -> dict[str, dict[str, Any]]:
    if generated_at is None:
        generated_at = _iso_now()

    preset_config = _load_preset_config(preset_id)
    if preset_config:
        print(f"[LLM Generation] Using preset: {preset_config.get('name', preset_id)}")
    else:
        print(f"[LLM Generation] WARNING: Could not load preset config for {preset_id}, using defaults")

    prompt = _build_generation_prompt(preset_id, preset_config)
    user_content = f"Preset: {preset_id}\nTranscript:\n{transcript}"

    provider_key = provider.strip().lower()
    raw_text = ""

    if provider_key == "openai":
        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        }
        response = _request_openai(payload)
        raw_text = _extract_openai_text(response)

    elif provider_key in {"gemini", "vertex"}:
        if vertexai is None:
            raise RuntimeError("vertexai SDK is not installed")

        try:
            project_id = os.getenv("GCP_PROJECT_ID", "delta-student-486911-n5")
            location = os.getenv("GCP_REGION", "global")
            if "gemini-3" in model:
                location = "global"

            vertexai.init(project=project_id, location=location)
            generative_model = GenerativeModel(model)

            response = generative_model.generate_content(
                [prompt, user_content],
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 1.0,
                    "max_output_tokens": 8192,
                },
            )
            raw_text = response.text

        except Exception as exc:
            print(f"[LLM Generation] Vertex AI Error: {exc}")
            raise RuntimeError(f"Vertex AI generation failed: {exc}")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"[LLM Generation] JSON Decode Error. Raw output:\n{raw_text[:200]}...")
        raise ValueError(f"LLM failed to return valid JSON: {exc}")

    mapping = {
        "summary": "summary",
        "outline": "outline",
        "key_terms": "key-terms",
        "flashcards": "flashcards",
        "exam_questions": "exam-questions",
    }

    artifacts: dict[str, dict[str, Any]] = {}
    for key, artifact_type in mapping.items():
        if key not in data:
            print(f"[LLM Generation] Warning: Missing '{key}' in LLM response.")
            continue

        artifact = data[key]
        if not isinstance(artifact, dict):
            print(f"[LLM Generation] Warning: Artifact '{key}' is not an object.")
            continue

        base = _base_artifact(
            artifact_type=artifact_type,
            course_id=course_id,
            lecture_id=lecture_id,
            preset_id=preset_id,
            generated_at=generated_at,
        )
        base.update(artifact)
        base["artifactType"] = artifact_type

        if thread_refs:
            base["threadRefs"] = thread_refs

        artifacts[artifact_type] = base

    return artifacts
