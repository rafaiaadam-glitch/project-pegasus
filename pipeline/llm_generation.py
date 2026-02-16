from __future__ import annotations

import json
import os
import uuid
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List

# Google Vertex AI Imports
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

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

def _extract_openai_text(response: Dict[str, Any]) -> str:
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

def _load_preset_config(preset_id: str) -> Dict[str, Any] | None:
    """Load preset configuration from backend/presets.py."""
    try:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        from presets import PRESETS_BY_ID
        return PRESETS_BY_ID.get(preset_id)
    except Exception as e:
        print(f"[LLM Generation] WARNING: Could not load preset {preset_id}: {e}")
        return None

def _build_generation_prompt(preset_id: str, preset_config: Dict[str, Any] | None) -> str:
    """Build a system prompt customized for the preset's generation config."""

    # Base structure requirement
    base_prompt = (
        "You are generating structured study artifacts for Pegasus Lecture Copilot.\n"
        "Return STRICT JSON only. You MUST return a JSON OBJECT (not an array) with these exact keys:\n"
        "summary, outline, key_terms, flashcards, exam_questions.\n\n"
        "All artifacts must include: id, courseId, lectureId, presetId, artifactType, generatedAt, version.\n\n"
    )

    # Add preset-specific generation instructions
    if preset_config and "generation_config" in preset_config:
        gen_config = preset_config["generation_config"]
        preset_name = preset_config.get("name", preset_id)

        base_prompt += f"\nMODE: {preset_name}\n"
        base_prompt += "=" * 60 + "\n\n"

        # Tone directive
        if "tone" in gen_config:
            tone_guidance = {
                "formal_academic": "Use formal academic language. Be precise and scholarly.",
                "conversational": "Use plain, everyday language. Explain like you're talking to a friend. Include examples and analogies.",
                "direct_predictable": "Use short, direct sentences (max 15 words). Use numbered steps. Avoid metaphors and ambiguity.",
                "analytical_precise": "Use precise technical language. Emphasize methodology and evidence.",
                "dialectical": "Present arguments and counterarguments. Attribute positions to speakers. Highlight points of disagreement.",
            }
            tone = gen_config["tone"]
            if tone in tone_guidance:
                base_prompt += f"TONE: {tone_guidance[tone]}\n\n"

        # Length targets
        if "summary_max_words" in gen_config:
            base_prompt += f"SUMMARY LENGTH: Target ~{gen_config['summary_max_words']} words maximum\n"
        if "flashcard_count" in gen_config:
            base_prompt += f"FLASHCARD COUNT: Generate approximately {gen_config['flashcard_count']} flashcards\n"
        if "exam_question_count" in gen_config:
            base_prompt += f"EXAM QUESTIONS: Generate approximately {gen_config['exam_question_count']} questions\n"

        # Question types
        if "question_types" in gen_config:
            q_types = ", ".join(gen_config["question_types"])
            base_prompt += f"QUESTION TYPES: Focus on {q_types}\n"

        # Special instructions
        if "special_instructions" in gen_config:
            base_prompt += "\nSPECIAL INSTRUCTIONS:\n"
            for instruction in gen_config["special_instructions"]:
                base_prompt += f"- {instruction}\n"

        base_prompt += "\n" + "=" * 60 + "\n\n"

    # Schema definitions
    base_prompt += (
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

    return base_prompt

def generate_artifacts_with_llm(
    transcript: str,
    preset_id: str,
    course_id: str,
    lecture_id: str,
    generated_at: str | None = None,
    model: str = "gemini-1.5-flash-002",  # Default to Gemini Flash on GCP
    thread_refs: List[str] | None = None,
    provider: str = "gemini",  # Default to Gemini/Vertex AI
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
        # --- FIXED: Use Native Vertex AI SDK ---
        try:
            # 1. Initialize Vertex AI (Uses GCP IAM Identity)
            # You can leave project/location as None if running on Cloud Run in the same project
            # or force them from environment variables if needed.
            project_id = os.getenv("GCP_PROJECT_ID", "delta-student-486911-n5")
            location = os.getenv("GCP_REGION", "us-central1")
            vertexai.init(project=project_id, location=location)

            # 2. Instantiate Model
            generative_model = GenerativeModel(model)
            print(f"[LLM Generation] Generating via Vertex AI model: {model}")

            # 3. Generate Content
            response = generative_model.generate_content(
                [prompt, user_content],
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            raw_text = response.text

        except Exception as e:
            print(f"[LLM Generation] Vertex AI Error: {e}")
            raise RuntimeError(f"Vertex AI generation failed: {e}")
        # ---------------------------------------
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
