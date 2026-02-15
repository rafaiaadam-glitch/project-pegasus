"""Tests for Gemini/Vertex AI LLM generation"""
from __future__ import annotations

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pipeline import llm_generation


def test_request_gemini_success(monkeypatch):
    """Test successful Gemini API request"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")

    fake_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"summary": "test", "outline": "test"}'}]
                }
            }
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fake_response).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = llm_generation._request_gemini(
            prompt="Test prompt",
            user_content="Test content",
            model="gemini-1.5-flash"
        )

        assert result == fake_response
        assert mock_urlopen.called


def test_request_gemini_uses_google_api_key_fallback(monkeypatch):
    """Test that GOOGLE_API_KEY is used when GEMINI_API_KEY is not set"""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    fake_response = {
        "candidates": [
            {"content": {"parts": [{"text": '{"summary": "test"}'}]}}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(fake_response).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = llm_generation._request_gemini(
            prompt="Test",
            user_content="Content",
            model="gemini-1.5-flash"
        )

        assert result == fake_response
        # Verify the URL contains the Google API key
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        assert "test-google-key" in request_obj.full_url


def test_request_gemini_missing_api_key(monkeypatch):
    """Test that missing API key raises RuntimeError"""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY or GOOGLE_API_KEY"):
        llm_generation._request_gemini(
            prompt="Test",
            user_content="Content",
            model="gemini-1.5-flash"
        )


def test_extract_gemini_text_success():
    """Test extracting text from Gemini API response"""
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Extracted text content"}]
                }
            }
        ]
    }

    result = llm_generation._extract_gemini_text(response)
    assert result == "Extracted text content"


def test_extract_gemini_text_missing_candidates():
    """Test that missing candidates raises ValueError"""
    response = {"candidates": []}

    with pytest.raises(ValueError, match="Gemini response missing text output"):
        llm_generation._extract_gemini_text(response)


def test_extract_gemini_text_missing_content():
    """Test that missing content raises ValueError"""
    response = {"candidates": [{}]}

    with pytest.raises(ValueError, match="Gemini response missing text output"):
        llm_generation._extract_gemini_text(response)


def test_extract_gemini_text_missing_parts():
    """Test that missing parts raises ValueError"""
    response = {"candidates": [{"content": {"parts": []}}]}

    with pytest.raises(ValueError, match="Gemini response missing text output"):
        llm_generation._extract_gemini_text(response)


def test_generate_artifacts_with_gemini_provider(monkeypatch):
    """Test artifact generation with Gemini provider"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("GCP_REGION", "us-central1")

    fake_artifacts = {
        "summary": {
            "id": "summary-1",
            "courseId": "course-1",
            "lectureId": "lecture-1",
            "presetId": "exam-mode",
            "artifactType": "summary",
            "overview": "Test overview",
            "sections": []
        },
        "outline": {
            "id": "outline-1",
            "courseId": "course-1",
            "lectureId": "lecture-1",
            "presetId": "exam-mode",
            "artifactType": "outline",
            "items": []
        },
        "key_terms": {
            "id": "terms-1",
            "courseId": "course-1",
            "lectureId": "lecture-1",
            "presetId": "exam-mode",
            "artifactType": "key-terms",
            "terms": []
        },
        "flashcards": {
            "id": "flash-1",
            "courseId": "course-1",
            "lectureId": "lecture-1",
            "presetId": "exam-mode",
            "artifactType": "flashcards",
            "cards": []
        },
        "exam_questions": {
            "id": "exam-1",
            "courseId": "course-1",
            "lectureId": "lecture-1",
            "presetId": "exam-mode",
            "artifactType": "exam-questions",
            "questions": []
        }
    }

    fake_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(fake_artifacts)}]
                }
            }
        ]
    }

    with patch("vertexai.init"):
        with patch.object(llm_generation, "_request_gemini", return_value=fake_gemini_response):
            result = llm_generation.generate_artifacts_with_llm(
                transcript="Test transcript",
                preset_id="exam-mode",
                course_id="course-1",
                lecture_id="lecture-1",
                provider="gemini",
                model="gemini-1.5-flash"
            )

            assert "summary" in result
            assert "outline" in result
            assert "key-terms" in result
            assert "flashcards" in result
            assert "exam-questions" in result

            # Verify artifact types are correctly set
            assert result["summary"]["artifactType"] == "summary"
            assert result["key-terms"]["artifactType"] == "key-terms"


def test_generate_artifacts_with_vertex_provider(monkeypatch):
    """Test that vertex provider uses same Gemini path"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("GCP_REGION", "us-west1")

    fake_artifacts = {
        "summary": {"artifactType": "summary"},
        "outline": {"artifactType": "outline"},
        "key_terms": {"artifactType": "key-terms"},
        "flashcards": {"artifactType": "flashcards"},
        "exam_questions": {"artifactType": "exam-questions"}
    }

    fake_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(fake_artifacts)}]}}
        ]
    }

    with patch.object(llm_generation, "_request_gemini", return_value=fake_response):
        result = llm_generation.generate_artifacts_with_llm(
            transcript="Test",
            preset_id="exam-mode",
            course_id="c1",
            lecture_id="l1",
            provider="vertex"  # Test vertex specifically
        )

        # Vertex provider should work and generate artifacts
        assert "summary" in result


def test_generate_artifacts_invalid_provider():
    """Test that invalid provider raises ValueError"""
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        llm_generation.generate_artifacts_with_llm(
            transcript="Test",
            preset_id="exam-mode",
            course_id="c1",
            lecture_id="l1",
            provider="invalid-provider"
        )


def test_generate_artifacts_invalid_json_response(monkeypatch):
    """Test that invalid JSON from LLM raises ValueError"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_response = {
        "candidates": [
            {"content": {"parts": [{"text": "Not valid JSON"}]}}
        ]
    }

    with patch("vertexai.init"):
        with patch.object(llm_generation, "_request_gemini", return_value=fake_response):
            with pytest.raises(ValueError, match="failed to return valid JSON"):
                llm_generation.generate_artifacts_with_llm(
                    transcript="Test",
                    preset_id="exam-mode",
                    course_id="c1",
                    lecture_id="l1",
                    provider="gemini"
                )


def test_generate_artifacts_missing_required_keys(monkeypatch):
    """Test that missing required artifact keys raises ValueError"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Missing 'outline' key
    incomplete_artifacts = {
        "summary": {"artifactType": "summary"},
        "key_terms": {"artifactType": "key-terms"}
    }

    fake_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(incomplete_artifacts)}]}}
        ]
    }

    with patch("vertexai.init"):
        with patch.object(llm_generation, "_request_gemini", return_value=fake_response):
            with pytest.raises(ValueError, match="Missing 'outline'"):
                llm_generation.generate_artifacts_with_llm(
                    transcript="Test",
                    preset_id="exam-mode",
                    course_id="c1",
                    lecture_id="l1",
                    provider="gemini"
                )


def test_generate_artifacts_with_thread_refs(monkeypatch):
    """Test that thread_refs are added to artifacts when provided"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_artifacts = {
        "summary": {"artifactType": "summary"},
        "outline": {"artifactType": "outline"},
        "key_terms": {"artifactType": "key-terms"},
        "flashcards": {"artifactType": "flashcards"},
        "exam_questions": {"artifactType": "exam-questions"}
    }

    fake_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(fake_artifacts)}]}}
        ]
    }

    with patch("vertexai.init"):
        with patch.object(llm_generation, "_request_gemini", return_value=fake_response):
            result = llm_generation.generate_artifacts_with_llm(
                transcript="Test",
                preset_id="exam-mode",
                course_id="c1",
                lecture_id="l1",
                provider="gemini",
                thread_refs=["thread-1", "thread-2"]
            )

            # All artifacts should have thread refs
            assert result["summary"]["threadRefs"] == ["thread-1", "thread-2"]
            assert result["outline"]["threadRefs"] == ["thread-1", "thread-2"]
            assert result["key-terms"]["threadRefs"] == ["thread-1", "thread-2"]


def test_gemini_uses_default_project_when_env_not_set(monkeypatch):
    """Test that Gemini works when GCP project env vars are not set"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GCP_REGION", raising=False)

    fake_artifacts = {
        "summary": {"artifactType": "summary"},
        "outline": {"artifactType": "outline"},
        "key_terms": {"artifactType": "key-terms"},
        "flashcards": {"artifactType": "flashcards"},
        "exam_questions": {"artifactType": "exam-questions"}
    }

    fake_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(fake_artifacts)}]}}
        ]
    }

    with patch.object(llm_generation, "_request_gemini", return_value=fake_response):
        result = llm_generation.generate_artifacts_with_llm(
            transcript="Test",
            preset_id="exam-mode",
            course_id="c1",
            lecture_id="l1",
            provider="gemini"
        )

        # Should work without GCP project env vars (uses REST API)
        assert "summary" in result
