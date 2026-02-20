"""LLM-based artifact generation for Pegasus pipeline."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.presets import PRESETS_BY_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_preset_config(preset_id: str) -> Optional[Dict[str, Any]]:
    """Load a preset configuration by ID."""
    return PRESETS_BY_ID.get(preset_id)


def _build_generation_prompt(preset_id: str, preset_config: Optional[Dict[str, Any]]) -> str:
    """Build the system prompt for artifact generation, customized by preset."""
    base_prompt = (
        "You are an expert academic content generator. "
        "Given a lecture transcript, produce structured study materials as JSON.\n\n"
        "Return a single JSON object with these keys:\n"
        "- \"summary\": {\"title\": str, \"text\": str, \"keyPoints\": [str]}\n"
        "- \"outline\": {\"title\": str, \"sections\": [{\"heading\": str, \"points\": [str]}]}\n"
        "- \"key_terms\": {\"terms\": [{\"term\": str, \"definition\": str}]}\n"
        "- \"flashcards\": {\"cards\": [{\"front\": str, \"back\": str}]}\n"
        "- \"exam_questions\": {\"questions\": [{\"question\": str, \"type\": str, "
        "\"options\": [str] | null, \"answer\": str, \"explanation\": str}]}\n\n"
    )

    if not preset_config:
        return base_prompt

    gen_config = preset_config.get("generation_config", {})
    if not gen_config:
        return base_prompt

    # Add preset-specific instructions
    mode_section = f"MODE: {preset_config.get('name', preset_id)}\n"
    mode_section += f"Description: {preset_config.get('description', '')}\n\n"

    if gen_config.get("tone"):
        mode_section += f"Tone: {gen_config['tone']}\n"
    if gen_config.get("summary_max_words"):
        mode_section += f"Summary max words: {gen_config['summary_max_words']}\n"
    if gen_config.get("flashcard_count"):
        mode_section += f"Target flashcard count: {gen_config['flashcard_count']}\n"
    if gen_config.get("exam_question_count"):
        mode_section += f"Target exam question count: {gen_config['exam_question_count']}\n"

    question_types = gen_config.get("question_types", [])
    if question_types:
        mode_section += f"Question types to include: {', '.join(question_types)}\n"

    special_instructions = gen_config.get("special_instructions", [])
    if special_instructions:
        mode_section += "\nSpecial instructions:\n"
        for instruction in special_instructions:
            mode_section += f"- {instruction}\n"

    return base_prompt + "=" * 60 + "\n" + mode_section + "=" * 60 + "\n"


def _base_artifact(
    artifact_type: str,
    course_id: str,
    lecture_id: str,
    preset_id: str,
    generated_at: str,
) -> Dict[str, Any]:
    """Create the base artifact envelope."""
    return {
        "id": str(uuid.uuid4()),
        "courseId": course_id,
        "lectureId": lecture_id,
        "presetId": preset_id,
        "artifactType": artifact_type,
        "generatedAt": generated_at,
        "version": "0.2",
    }


def _request_openai(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a request to the OpenAI API."""
    import urllib.request

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def _extract_openai_text(response: Dict[str, Any]) -> str:
    """Extract text content from an OpenAI API response."""
    # Handle Responses API format
    output = response.get("output", [])
    for item in output:
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return content.get("text", "")
    # Fallback: Chat Completions API format
    choices = response.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return ""


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def generate_artifacts_with_llm(
    transcript: str,
    preset_id: str,
    course_id: str,
    lecture_id: str,
    generated_at: str | None = None,
    model: str = "gemini-3-pro-preview",
    thread_refs: List[str] | None = None,
    provider: str = "gemini",
) -> Dict[str, Dict[str, Any]]:
    if generated_at is None:
        generated_at = _iso_now()

    # Load preset configuration
    preset_config = _load_preset_config(preset_id)
    if preset_config:
        print(f"[LLM Generation] Using preset: {preset_config.get('name', preset_id)}")
    else:
        print(f"[LLM Generation] WARNING: Could not load preset config for {preset_id}, using defaults")

    # Build customized prompt
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
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel, GenerationConfig

            project_id = os.getenv("GCP_PROJECT_ID", "delta-student-486911-n5")
            llm_region = os.getenv("PLC_LLM_REGION", os.getenv("GCP_REGION", "us-central1"))
            vertexai.init(project=project_id, location=llm_region)

            generative_model = GenerativeModel(model)
            print(f"[LLM Generation] Generating via Vertex AI model: {model}")

            response = generative_model.generate_content(
                [prompt, user_content],
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    thinking_budget=32000,
                    temperature=1.0,
                    max_output_tokens=8192,
                ),
            )
            raw_text = response.text

        except Exception as e:
            print(f"[LLM Generation] Vertex AI Error: {e}")
            raise RuntimeError(f"Vertex AI generation failed: {e}")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"[LLM Generation] JSON Decode Error. Raw output:\n{raw_text[:200]}...")
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
