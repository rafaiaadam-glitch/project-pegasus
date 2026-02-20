"""Tests for OpenAI integration in thread_engine"""
from __future__ import annotations

import json
import pytest
from unittest.mock import Mock, patch
from pipeline import thread_engine


def test_call_openai_success(monkeypatch):
    """Test successful OpenAI thread detection call"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

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

    fake_openai_response = {
        "output": [
            {
                "content": [{"text": json.dumps(fake_response)}]
            }
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_openai_response).encode("utf-8")
        mock_http_response.getcode.return_value = 200
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        result = thread_engine._call_openai(
            transcript="Test transcript",
            existing_threads=[],
            model="gpt-4o-mini"
        )

        assert result == fake_response
        assert "newThreads" in result
        assert len(result["newThreads"]) == 1
        assert result["newThreads"][0]["title"] == "Test Thread"


def test_call_openai_with_existing_threads(monkeypatch):
    """Test OpenAI thread detection with existing threads"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

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

    fake_openai_response = {
        "output": [
            {"content": [{"text": json.dumps(fake_response)}]}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_openai_response).encode("utf-8")
        mock_http_response.getcode.return_value = 200
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        result = thread_engine._call_openai(
            transcript="Test transcript continuing thread-1",
            existing_threads=existing_threads,
            model="gpt-4o-mini"
        )

        assert "updates" in result
        assert len(result["updates"]) == 1
        assert result["updates"][0]["threadId"] == "thread-1"

        # Verify that existing thread summary was passed to API
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        user_content = body["input"][1]["content"]
        assert "Existing Thread" in user_content


def test_call_openai_missing_api_key(monkeypatch):
    """Test that missing API key raises RuntimeError"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        thread_engine._call_openai(
            transcript="Test",
            existing_threads=[],
            model="gpt-4o-mini"
        )


def test_call_openai_empty_response(monkeypatch):
    """Test that empty OpenAI response raises error"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    fake_openai_response = {"output": []}

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_openai_response).encode("utf-8")
        mock_http_response.getcode.return_value = 200
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        with pytest.raises(RuntimeError, match="OpenAI thread detection failed"):
            thread_engine._call_openai(
                transcript="Test",
                existing_threads=[],
                model="gpt-4o-mini"
            )


def test_call_openai_invalid_json_in_response(monkeypatch):
    """Test that invalid JSON in OpenAI response raises error"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    fake_openai_response = {
        "output": [
            {"content": [{"text": "Not valid JSON"}]}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_openai_response).encode("utf-8")
        mock_http_response.getcode.return_value = 200
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        with pytest.raises(RuntimeError, match="OpenAI thread detection failed"):
            thread_engine._call_openai(
                transcript="Test",
                existing_threads=[],
                model="gpt-4o-mini"
            )


def test_call_openai_uses_json_response_format(monkeypatch):
    """Test that OpenAI is configured to return JSON"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    fake_response = {"newThreads": [], "updates": []}
    fake_openai_response = {
        "output": [
            {"content": [{"text": json.dumps(fake_response)}]}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_openai_response).encode("utf-8")
        mock_http_response.getcode.return_value = 200
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        thread_engine._call_openai(
            transcript="Test",
            existing_threads=[],
            model="gpt-4o-mini"
        )

        # Verify request payload has JSON format
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        assert body["text"]["format"]["type"] == "json_object"


def test_call_openai_includes_system_prompt(monkeypatch):
    """Test that system prompt is included in OpenAI request"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    fake_response = {"newThreads": [], "updates": []}
    fake_openai_response = {
        "output": [
            {"content": [{"text": json.dumps(fake_response)}]}
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_http_response = Mock()
        mock_http_response.read.return_value = json.dumps(fake_openai_response).encode("utf-8")
        mock_http_response.getcode.return_value = 200
        mock_http_response.__enter__ = Mock(return_value=mock_http_response)
        mock_http_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_http_response

        thread_engine._call_openai(
            transcript="Test",
            existing_threads=[],
            model="gpt-4o-mini"
        )

        # Verify system message is present
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        assert body["input"][0]["role"] == "system"
        assert len(body["input"][0]["content"]) > 0
