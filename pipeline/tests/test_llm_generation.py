"""Tests for Vertex AI LLM generation

Note: Tests for the old _request_gemini and _extract_gemini_text functions have been removed.
The implementation now uses the Vertex AI SDK directly, which is tested via integration tests.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pipeline import llm_generation


def test_generate_artifacts_invalid_provider():
    """Test that invalid provider raises ValueError"""
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        llm_generation.generate_artifacts_with_llm(
            transcript="Test transcript",
            preset_id="exam",
            course_id="course-1",
            lecture_id="lecture-1",
            provider="invalid-provider"
        )


def test_base_artifact_structure():
    """Test that _base_artifact generates correct structure"""
    result = llm_generation._base_artifact(
        artifact_type="summary",
        course_id="course-123",
        lecture_id="lecture-456",
        preset_id="exam",
        generated_at="2024-01-01T00:00:00Z"
    )

    assert result["artifactType"] == "summary"
    assert result["courseId"] == "course-123"
    assert result["lectureId"] == "lecture-456"
    assert result["presetId"] == "exam"
    assert result["generatedAt"] == "2024-01-01T00:00:00Z"
    assert result["version"] == "0.2"
    assert "id" in result


def test_build_generation_prompt_includes_required_structures():
    """Test that prompt includes all required artifact structures"""
    prompt = llm_generation._build_generation_prompt("exam", None)

    assert "summary" in prompt
    assert "outline" in prompt
    assert "key_terms" in prompt
    assert "flashcards" in prompt
    assert "exam_questions" in prompt
    assert "artifactType" in prompt


def test_build_generation_prompt_with_preset_config():
    """Test that preset config modifies the prompt"""
    preset_config = {
        "name": "Test Mode",
        "generation_config": {
            "tone": "conversational",
            "summary_max_words": 300,
            "flashcard_count": 15,
            "exam_question_count": 10,
            "question_types": ["multiple-choice", "short-answer"],
            "special_instructions": ["Focus on practical examples"]
        }
    }

    prompt = llm_generation._build_generation_prompt("test", preset_config)

    assert "Test Mode" in prompt
    assert "conversational" in prompt or "plain, everyday language" in prompt
    assert "300" in prompt
    assert "15" in prompt
    assert "10" in prompt
    assert "practical examples" in prompt


@patch('pipeline.llm_generation.vertexai')
@patch('pipeline.llm_generation.GenerativeModel')
def test_generate_artifacts_with_vertex_ai(mock_model_class, mock_vertexai, monkeypatch):
    """Test artifact generation with Vertex AI SDK"""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("GCP_REGION", "us-central1")

    # Mock the Vertex AI response
    mock_model_instance = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "summary": {
            "overview": "Test overview",
            "sections": [{"title": "Section 1", "bullets": ["Point 1"]}]
        },
        "outline": {
            "outline": [{"title": "Topic 1", "points": ["Detail 1"], "children": []}]
        },
        "key_terms": {
            "terms": [{"term": "Term 1", "definition": "Definition 1"}]
        },
        "flashcards": {
            "cards": [{"front": "Question?", "back": "Answer"}]
        },
        "exam_questions": {
            "questions": [{
                "prompt": "Test question?",
                "type": "multiple-choice",
                "answer": "A",
                "choices": ["A", "B", "C"],
                "correctChoiceIndex": 0
            }]
        }
    })

    mock_model_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model_instance

    result = llm_generation.generate_artifacts_with_llm(
        transcript="Test transcript about photosynthesis",
        preset_id="exam",
        course_id="bio-101",
        lecture_id="lecture-1",
        provider="vertex"
    )

    # Verify Vertex AI was initialized
    mock_vertexai.init.assert_called_once()

    # Verify model was instantiated
    mock_model_class.assert_called_once()

    # Verify artifacts were generated
    assert "summary" in result
    assert "outline" in result
    assert "key-terms" in result
    assert "flashcards" in result
    assert "exam-questions" in result

    # Verify artifact structure
    assert result["summary"]["artifactType"] == "summary"
    assert result["summary"]["courseId"] == "bio-101"
    assert result["summary"]["lectureId"] == "lecture-1"
    assert result["summary"]["presetId"] == "exam"
    assert "overview" in result["summary"]


@patch('pipeline.llm_generation.vertexai')
@patch('pipeline.llm_generation.GenerativeModel')
def test_generate_artifacts_with_thread_refs(mock_model_class, mock_vertexai, monkeypatch):
    """Test that thread_refs are included in artifacts"""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

    mock_model_instance = Mock()
    mock_response = Mock()
    mock_response.text = json.dumps({
        "summary": {"overview": "Test", "sections": []},
        "outline": {"outline": []},
        "key_terms": {"terms": []},
        "flashcards": {"cards": []},
        "exam_questions": {"questions": []}
    })

    mock_model_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model_instance

    thread_refs = ["thread-1", "thread-2", "thread-3"]
    result = llm_generation.generate_artifacts_with_llm(
        transcript="Test",
        preset_id="exam",
        course_id="course-1",
        lecture_id="lecture-1",
        thread_refs=thread_refs,
        provider="gemini"
    )

    # Verify thread refs are in all artifacts
    for artifact in result.values():
        assert "threadRefs" in artifact
        assert artifact["threadRefs"] == thread_refs


@patch('pipeline.llm_generation.vertexai')
@patch('pipeline.llm_generation.GenerativeModel')
def test_generate_artifacts_handles_missing_keys(mock_model_class, mock_vertexai, monkeypatch, capsys):
    """Test that missing keys in LLM response are handled gracefully"""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

    mock_model_instance = Mock()
    mock_response = Mock()
    # Response missing 'flashcards' and 'exam_questions'
    mock_response.text = json.dumps({
        "summary": {"overview": "Test", "sections": []},
        "outline": {"outline": []},
        "key_terms": {"terms": []}
    })

    mock_model_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model_instance

    result = llm_generation.generate_artifacts_with_llm(
        transcript="Test",
        preset_id="exam",
        course_id="course-1",
        lecture_id="lecture-1",
        provider="gemini"
    )

    # Should have 3 artifacts
    assert len(result) == 3
    assert "summary" in result
    assert "outline" in result
    assert "key-terms" in result

    # Should not have missing artifacts
    assert "flashcards" not in result
    assert "exam-questions" not in result

    # Should print warnings
    captured = capsys.readouterr()
    assert "Missing 'flashcards'" in captured.out
    assert "Missing 'exam_questions'" in captured.out


@patch('pipeline.llm_generation.vertexai')
@patch('pipeline.llm_generation.GenerativeModel')
def test_vertex_ai_error_handling(mock_model_class, mock_vertexai, monkeypatch):
    """Test that Vertex AI errors are handled properly"""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

    mock_model_instance = Mock()
    mock_model_instance.generate_content.side_effect = Exception("Vertex AI API Error")
    mock_model_class.return_value = mock_model_instance

    with pytest.raises(RuntimeError, match="Vertex AI generation failed"):
        llm_generation.generate_artifacts_with_llm(
            transcript="Test",
            preset_id="exam",
            course_id="course-1",
            lecture_id="lecture-1",
            provider="vertex"
        )


@patch('pipeline.llm_generation.vertexai')
@patch('pipeline.llm_generation.GenerativeModel')
def test_vertex_ai_invalid_json_response(mock_model_class, mock_vertexai, monkeypatch):
    """Test that invalid JSON responses are handled"""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

    mock_model_instance = Mock()
    mock_response = Mock()
    mock_response.text = "This is not valid JSON"

    mock_model_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model_instance

    with pytest.raises(ValueError, match="LLM failed to return valid JSON"):
        llm_generation.generate_artifacts_with_llm(
            transcript="Test",
            preset_id="exam",
            course_id="course-1",
            lecture_id="lecture-1",
            provider="gemini"
        )
