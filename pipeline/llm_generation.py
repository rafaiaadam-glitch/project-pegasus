from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

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
    model: str = "gemini-1.5-flash",  # Defaulting to Gemini on GCP
    thread_refs: List[str] | None = None,
) -> Dict[str, Dict[str, Any]]:
    if generated_at is None:
        generated_at = _iso_now()

    # Initialize Vertex AI using your project ID from GCP_DEPLOYMENT.md
    project_id = os.getenv("GCP_PROJECT_ID", "delta-student-486911-n5")
    location = os.getenv("GCP_REGION", "us-central1")
    vertexai.init(project=project_id, location=location)

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

    # Setup Gemini model with JSON response format
    generative_model = GenerativeModel(model)
    
    user_content = f"Preset: {preset_id}\nTranscript:\n{transcript}"
    
    response = generative_model.generate_content(
        [prompt, user_content],
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini failed to return valid JSON: {e}")

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
