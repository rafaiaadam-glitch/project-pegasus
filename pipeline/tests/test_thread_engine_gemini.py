"""Tests for Gemini integration in thread_engine"""
from __future__ import annotations

import json
import pytest
from unittest.mock import Mock, patch
from pipeline import thread_engine


def test_call_gemini_success(monkeypatch):
    """Test successful Gemini thread detection call"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")

    fake_response = {
        "newThreads": [
            {
                "title": "Test Thread",
                "summary": "Summary of test thread",
                "concepts": ["concept1", "concept2"]
            }
        ],
        "updates": []
    }

    fake_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(fake_response)}]
                }
            }
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_gemini_response).encode("utf-8")
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        result = thread_engine._call_gemini(
            transcript="Test transcript",
            existing_threads=[],
            model="gemini-1.5-flash"
        )

        assert result == fake_response
        assert "newThreads" in result
        assert len(result["newThreads"]) == 1
        assert result["newThreads"][0]["title"] == "Test Thread"


def test_call_gemini_with_existing_threads(monkeypatch):
    """Test Gemini thread detection with existing threads"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")

    existing_threads = [
        {
            "id": "thread-1",
            "title": "Existing Thread",
            "summary": "Summary of existing thread"
        }
    ]

    fake_response = {
        "newThreads": [],
        "updates": [
            {
                "threadId": "thread-1",
                "changeType": "extension",
                "updatedSummary": "Updated summary"
            }
        ]
    }

    fake_gemini_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(fake_response)}]}}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_gemini_response).encode("utf-8")
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        result = thread_engine._call_gemini(
            transcript="Test transcript continuing thread-1",
            existing_threads=existing_threads,
            model="gemini-1.5-flash"
        )

        assert "updates" in result
        assert len(result["updates"]) == 1
        assert result["updates"][0]["threadId"] == "thread-1"

        # Verify that existing thread summary was passed to API
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        user_content = body["contents"][0]["parts"][0]["text"]
        assert "Existing Thread" in user_content


def test_call_gemini_uses_google_api_key_fallback(monkeypatch):
    """Test that GOOGLE_API_KEY is used when GEMINI_API_KEY not set"""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    fake_response = {"newThreads": [], "updates": []}
    fake_gemini_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(fake_response)}]}}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_gemini_response).encode("utf-8")
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        result = thread_engine._call_gemini(
            transcript="Test",
            existing_threads=[],
            model="gemini-1.5-flash"
        )

        assert result == fake_response
        # Verify URL contains Google API key
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "test-google-key" in request.full_url


def test_call_gemini_missing_api_key(monkeypatch):
    """Test that missing API keys raises RuntimeError"""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY or GOOGLE_API_KEY"):
        thread_engine._call_gemini(
            transcript="Test",
            existing_threads=[],
            model="gemini-1.5-flash"
        )


def test_call_gemini_empty_response(monkeypatch):
    """Test that empty Gemini response raises RuntimeError"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Response with no extractable text
    fake_gemini_response = {
        "candidates": []
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_gemini_response).encode("utf-8")
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        with pytest.raises(RuntimeError, match="Gemini thread detection failed"):
            thread_engine._call_gemini(
                transcript="Test",
                existing_threads=[],
                model="gemini-1.5-flash"
            )


def test_call_gemini_invalid_json_in_response(monkeypatch):
    """Test that invalid JSON in Gemini response raises RuntimeError"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_gemini_response = {
        "candidates": [
            {"content": {"parts": [{"text": "Not valid JSON"}]}}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_gemini_response).encode("utf-8")
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        with pytest.raises(RuntimeError, match="Gemini thread detection failed"):
            thread_engine._call_gemini(
                transcript="Test",
                existing_threads=[],
                model="gemini-1.5-flash"
            )


def test_call_gemini_uses_json_response_mime_type(monkeypatch):
    """Test that Gemini is configured to return JSON"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_response = {"newThreads": [], "updates": []}
    fake_gemini_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(fake_response)}]}}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_gemini_response).encode("utf-8")
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        thread_engine._call_gemini(
            transcript="Test",
            existing_threads=[],
            model="gemini-1.5-flash"
        )

        # Verify request payload has JSON MIME type
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        assert body["generationConfig"]["responseMimeType"] == "application/json"


def test_call_gemini_includes_system_prompt(monkeypatch):
    """Test that system prompt is included in Gemini request"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_response = {"newThreads": [], "updates": []}
    fake_gemini_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(fake_response)}]}}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_gemini_response).encode("utf-8")
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        thread_engine._call_gemini(
            transcript="Test",
            existing_threads=[],
            model="gemini-1.5-flash"
        )

        # Verify system instruction is present
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        assert "system_instruction" in body
        assert "parts" in body["system_instruction"]
        assert len(body["system_instruction"]["parts"]) > 0


def test_generate_thread_records_with_gemini_provider(monkeypatch):
    """Test generate_thread_records uses Gemini when provider=gemini"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_llm_output = {
        "newThreads": [
            {
                "title": "Machine Learning Basics",
                "summary": "Introduction to ML concepts",
                "concepts": ["supervised learning", "neural networks"]
            }
        ],
        "updates": []
    }

    fake_gemini_response = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(fake_llm_output)}]}}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_gemini_response).encode("utf-8")
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        # generate_thread_records returns a list of thread records, not the raw LLM output
        # The function processes the LLM output, so we just verify it calls Gemini
        result = thread_engine.generate_thread_records(
            transcript="Test transcript",
            existing_threads=[],
            lecture_id="lecture-1",
            course_id="course-1",
            provider="gemini",
            model="gemini-1.5-flash"
        )

        # Should have called the API
        assert mock_urlopen.called
        # Result should be a list
        assert isinstance(result, list)


def test_generate_thread_records_fallback_on_gemini_failure(monkeypatch):
    """Test that generate_thread_records falls back to keyword extraction when Gemini fails"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Make Gemini call fail
    def mock_call_gemini(*args, **kwargs):
        raise RuntimeError("Gemini API unavailable")

    with patch.object(thread_engine, "_call_gemini", side_effect=mock_call_gemini):
        # Should fall back to keyword extraction without raising
        result = thread_engine.generate_thread_records(
            transcript="Test transcript about machine learning and neural networks",
            existing_threads=[],
            lecture_id="lecture-1",
            course_id="course-1",
            provider="gemini",
            model="gemini-1.5-flash"
        )

        # Should return a list (may be empty or have keyword-based threads)
        assert isinstance(result, list)
