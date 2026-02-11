"""Pytest configuration and shared fixtures for pipeline tests."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_transcript():
    """Sample lecture transcript for testing."""
    return """
    Topic: Introduction to Machine Learning.

    Today we covered supervised learning, unsupervised learning, and reinforcement learning.
    We defined key concepts like training data, features, and labels. We emphasized the
    importance of data quality and the bias-variance tradeoff.

    We discussed how neural networks process information through layers and how backpropagation
    enables learning. We also introduced the concept of overfitting and regularization techniques.
    """.strip()


@pytest.fixture
def valid_summary_artifact():
    """Valid summary artifact matching schema."""
    return {
        "id": "test-summary-001",
        "courseId": "test-course",
        "lectureId": "test-lecture",
        "presetId": "exam-mode",
        "artifactType": "summary",
        "generatedAt": "2026-02-11T10:00:00+00:00",
        "version": "0.2",
        "threadRefs": ["thread-001", "thread-002"],
        "overview": "Introduction to core machine learning concepts.",
        "sections": [
            {
                "title": "Key Concepts",
                "bullets": [
                    "Supervised learning uses labeled data",
                    "Unsupervised learning finds patterns"
                ]
            }
        ]
    }


@pytest.fixture
def valid_thread():
    """Valid thread matching schema."""
    return {
        "id": "thread-001",
        "courseId": "test-course",
        "title": "Supervised Learning",
        "summary": "Learning from labeled examples",
        "status": "foundational",
        "complexityLevel": 2,
        "lectureRefs": ["test-lecture"],
        "evolutionNotes": []
    }


@pytest.fixture
def schema_dir(temp_dir):
    """Create temporary schema directory with test schemas."""
    schema_path = temp_dir / "schemas"
    schema_path.mkdir()

    # Create a simple test schema
    test_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"}
        },
        "required": ["id", "name"]
    }

    with open(schema_path / "test.schema.json", "w") as f:
        json.dump(test_schema, f)

    return schema_path
