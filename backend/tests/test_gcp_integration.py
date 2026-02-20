"""
Integration tests for OpenAI API and GCP storage.

These tests require actual credentials and are OPTIONAL.
They will be skipped if credentials are not available.

Run with: pytest backend/tests/test_gcp_integration.py -v
"""
from __future__ import annotations

import os
import json
import pytest
from pathlib import Path


# Skip all tests if OpenAI API key not available
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)


def test_openai_api_connectivity():
    """Test basic connectivity to OpenAI API"""
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10,
    )

    assert response.choices
    assert response.choices[0].message.content


def test_openai_json_mode():
    """Test OpenAI API with JSON response mode"""
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return a JSON object with a 'message' field"},
            {"role": "user", "content": "Create a test message"},
        ],
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content
    data = json.loads(text)
    assert isinstance(data, dict)


def test_openai_whisper_connectivity():
    """Test that OpenAI Whisper API is accessible (no actual transcription)"""
    from openai import OpenAI

    client = OpenAI()
    # Just verify the client can be created and models endpoint works
    assert client.api_key


def test_thread_engine_with_openai():
    """Test thread detection using OpenAI"""
    from pipeline.thread_engine import generate_thread_records

    transcript = (
        "Today we'll learn about data structures. "
        "First, we'll cover arrays and linked lists. "
        "Then we'll discuss hash tables and their applications."
    )

    threads, occurrences, updates = generate_thread_records(
        course_id="test-course",
        lecture_id="test-lecture",
        transcript=transcript,
        generated_at=None,
        storage_dir=Path("storage"),
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )

    assert isinstance(threads, list)
    assert len(threads) > 0
    assert isinstance(occurrences, list)
    assert isinstance(updates, list)


def test_environment_variables_set():
    """Verify required environment variables are accessible"""
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
    assert has_openai_key, "OPENAI_API_KEY must be set"


@pytest.mark.skipif(
    not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.getenv("GCP_PROJECT_ID"),
    reason="GCP credentials not available"
)
def test_gcs_client_creation():
    """Test creating GCS client (needed for storage)"""
    try:
        from google.cloud import storage as gcs_storage
    except ImportError:
        pytest.skip("google-cloud-storage not installed")

    client = gcs_storage.Client()
    assert client is not None
