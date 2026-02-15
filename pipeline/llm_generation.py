from __future__ import annotations

import json
import os
import uuid
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _request_openai(payload: Dict[str, Any], timeout: int = 90) -> Dict[str, Any]:
    from pipeline.retry_utils import NonRetryableError, retry_config_from_env, with_retry

    def make_request() -> Dict[str, Any]:
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    config = retry_config_from_env()

    try:
        return with_retry(make_request, config=config, operation_name="OpenAI API request")
    except NonRetryableError as e:
        raise RuntimeError(f"OpenAI API request failed: {e}") from e


def _request_gemini(prompt: str, user_content: str, model: str, timeout: int = 90) -> Dict[str, Any]:
    from pipeline.retry_utils import NonRetryableError, retry_config_from_env, with_retry

    def make_request() -> Dict[str, Any]:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Missing required environment variable: GEMINI_API_KEY or GOOGLE_API_KEY")

        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(api_key)}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    config = retry_config_from_env()

    try:
        return with_retry(make_request, config=config, operation_name="Gemini API request")
    except NonRetryableError as e:
        raise RuntimeError(f"Gemini API request failed: {e}") from e


def _extract_openai_text(response: Dict[str, Any]) -> str:
    for output in response.get("output", []):
        for content in output.get("content", []):
            if "text" in content:
                return content["text"]
    raise ValueError("OpenAI response missing text output.")


def _extract_gemini_text(response: Dict[str, Any]) -> str:
    for candidate in response.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                return text
    raise ValueError("Gemini response missing text output.")


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
    model: str = "gemini-1.5-flash",  # Default to Gemini on GCP
    thread_refs: List[str] | None = None,
    provider: str = "gemini",  # Default to Gemini/Vertex AI for GCP alignment
) -> Dict[str, Dict[str, Any]]:
    if generated_at is None:
        generated_at = _iso_now()

    prompt = (
        "You are generating structured study artifacts for Pegasus Lecture Copilot.\n"
        "Return STRICT JSON only. You MUST return a JSON OBJECT (not an array) with these exact keys:\n"
        "summary, outline, key_terms, flashcards, exam_questions.\n\n"
        "All artifacts must include: id, courseId, lectureId, presetId, artifactType, generatedAt, version.\n\n"
        "EXACT STRUCTURES REQUIRED:\n\n"
        '1. summary (artifactType: "summary"):\n'
        '   {\n'
        '     "id": "uuid", "courseId": "...", "lectureId": "...", "presetId": "...",\n'
        '     "artifactType": "summary", "generatedAt": "ISO date", "version": "0.2",\n'
        '     "overview": "Brief overview paragraph",\n'
        '     "sections": [\n'
        '       {"title": "Section Title", "bullets": ["Point 1", "Point 2"]}\n'
        '     ]\n'
        '   }\n\n'
        '2. outline (artifactType: "outline"):\n'
        '   {\n'
        '     "id": "uuid", "courseId": "...", "lectureId": "...", "presetId": "...",\n'
        '     "artifactType": "outline", "generatedAt": "ISO date", "version": "0.2",\n'
        '     "outline": [\n'
        '       {"title": "Main Topic", "points": ["Detail 1"], "children": [...]}\n'
        '     ]\n'
        '   }\n\n'
        '3. key_terms (artifactType: "key-terms"):\n'
        '   {\n'
        '     "id": "uuid", "courseId": "...", "lectureId": "...", "presetId": "...",\n'
        '     "artifactType": "key-terms", "generatedAt": "ISO date", "version": "0.2",\n'
        '     "terms": [\n'
        '       {"term": "Term Name", "definition": "Definition text"}\n'
        '     ]\n'
        '   }\n\n'
        '4. flashcards (artifactType: "flashcards"):\n'
        '   {\n'
        '     "id": "uuid", "courseId": "...", "lectureId": "...", "presetId": "...",\n'
        '     "artifactType": "flashcards", "generatedAt": "ISO date", "version": "0.2",\n'
        '     "cards": [\n'
        '       {"front": "Question?", "back": "Answer"}\n'
        '     ]\n'
        '   }\n\n'
        '5. exam_questions (artifactType: "exam-questions"):\n'
        '   {\n'
        '     "id": "uuid", "courseId": "...", "lectureId": "...", "presetId": "...",\n'
        '     "artifactType": "exam-questions", "generatedAt": "ISO date", "version": "0.2",\n'
        '     "questions": [\n'
        '       {"prompt": "Question?", "type": "multiple-choice", "answer": "Correct answer",\n'
        '        "choices": ["A", "B", "C"], "correctChoiceIndex": 0}\n'
        '     ]\n'
        '   }\n\n'
        "Generate artifacts from the transcript below.\n"
    )

    user_content = f"Preset: {preset_id}\nTranscript:\n{transcript}"
    provider_key = provider.strip().lower()

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
        response = _request_gemini(prompt=prompt, user_content=user_content, model=model)
        raw_text = _extract_gemini_text(response)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM failed to return valid JSON: {e}")

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
        
        if thread_refs:
            base["threadRefs"] = thread_refs
            
        artifacts[artifact_type] = base

    return artifacts
