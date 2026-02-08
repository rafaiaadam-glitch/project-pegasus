from __future__ import annotations

import json
import os
import uuid
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _request_openai(payload: Dict[str, Any]) -> Dict[str, Any]:
    api_key = _require_env("OPENAI_API_KEY")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_text(response: Dict[str, Any]) -> str:
    for output in response.get("output", []):
        for content in output.get("content", []):
            if "text" in content:
                return content["text"]
    raise ValueError("OpenAI response missing text output.")


def _base_artifact(
    artifact_type: str,
    course_id: str,
    lecture_id: str,
    preset_id: str,
    generated_at: str,
) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "courseId": course_id,
        "lectureId": lecture_id,
        "presetId": preset_id,
        "artifactType": artifact_type,
        "generatedAt": generated_at,
        "version": "0.2",
    }


def generate_artifacts_with_llm(
    transcript: str,
    preset_id: str,
    course_id: str,
    lecture_id: str,
    generated_at: str | None = None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Dict[str, Any]]:
    if generated_at is None:
        generated_at = _iso_now()

    prompt = (
        "You are generating structured study artifacts for Pegasus Lecture Copilot.\n"
        "Return STRICT JSON only. Produce an object with keys:\n"
        "summary, outline, key_terms, flashcards, exam_questions.\n"
        "Each value must match these rules:\n"
        "- Include metadata fields: id, courseId, lectureId, presetId, artifactType,\n"
        "  generatedAt, version.\n"
        "- artifactType must be one of: summary, outline, key-terms, flashcards, exam-questions.\n"
        "- Use presetId to change structure and emphasis.\n"
        "Use the transcript below to generate content.\n"
    )

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Preset: {preset_id}\nTranscript:\n{transcript}",
            },
        ],
        "response_format": {"type": "json_object"},
    }

    response = _request_openai(payload)
    raw_text = _extract_text(response)
    data = json.loads(raw_text)

    mapping = {
        "summary": "summary",
        "outline": "outline",
        "key_terms": "key-terms",
        "flashcards": "flashcards",
        "exam_questions": "exam-questions",
    }

    artifacts: Dict[str, Dict[str, Any]] = {}
    for key, artifact_type in mapping.items():
        if key not in data:
            raise ValueError(f"Missing '{key}' in LLM response.")
        artifact = data[key]
        if not isinstance(artifact, dict):
            raise ValueError(f"Artifact '{key}' must be an object.")
        base = _base_artifact(
            artifact_type=artifact_type,
            course_id=course_id,
            lecture_id=lecture_id,
            preset_id=preset_id,
            generated_at=generated_at,
        )
        base.update(artifact)
        base["artifactType"] = artifact_type
        artifacts[artifact_type] = base

    return artifacts
