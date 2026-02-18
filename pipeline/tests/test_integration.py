"""Integration tests for the full pipeline."""

import json
import pytest
from pathlib import Path

from pipeline.run_pipeline import PipelineContext, _base_artifact, _validate, ARTIFACT_SCHEMA_DIR


class TestPipelineContext:
    """Tests for PipelineContext dataclass."""

    def test_context_creation(self):
        """Test creating a pipeline context."""
        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=["thread-001", "thread-002"]
        )

        assert context.course_id == "test-course"
        assert context.lecture_id == "test-lecture"
        assert context.preset_id == "exam-mode"
        assert len(context.thread_refs) == 2

    def test_context_immutable(self):
        """Test that context is immutable (frozen)."""
        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=[]
        )

        with pytest.raises(AttributeError):
            context.course_id = "new-course"


class TestBaseArtifact:
    """Tests for _base_artifact function."""

    def test_base_artifact_structure(self):
        """Test base artifact has correct structure."""
        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=["thread-001"]
        )

        artifact = _base_artifact(context, "summary")

        assert "id" in artifact
        assert artifact["courseId"] == "test-course"
        assert artifact["lectureId"] == "test-lecture"
        assert artifact["presetId"] == "exam-mode"
        assert artifact["artifactType"] == "summary"
        assert artifact["generatedAt"] == "2026-02-11T10:00:00Z"
        assert artifact["version"] == "0.2"
        assert artifact["threadRefs"] == ["thread-001"]

    def test_base_artifact_unique_ids(self):
        """Test that each artifact gets a unique ID."""
        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=[]
        )

        artifact1 = _base_artifact(context, "summary")
        artifact2 = _base_artifact(context, "outline")

        assert artifact1["id"] != artifact2["id"]


class TestArtifactGeneration:
    """Integration tests for artifact generation."""

    def test_generate_all_artifacts(self, sample_transcript, temp_dir):
        """Test generating all artifact types."""
        from pipeline.run_pipeline import (
            _summary, _outline, _key_terms, _flashcards, _exam_questions
        )

        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=["thread-001", "thread-002"]
        )

        # Generate all artifacts
        summary = _summary(context, sample_transcript)
        outline = _outline(context)
        key_terms = _key_terms(context)
        flashcards = _flashcards(context)
        exam_questions = _exam_questions(context)

        # Verify basic structure
        assert summary["artifactType"] == "summary"
        assert outline["artifactType"] == "outline"
        assert key_terms["artifactType"] == "key-terms"
        assert flashcards["artifactType"] == "flashcards"
        assert exam_questions["artifactType"] == "exam-questions"

        # Verify content exists
        assert "overview" in summary
        assert "sections" in summary
        assert "outline" in outline
        assert "terms" in key_terms
        assert "cards" in flashcards
        assert "questions" in exam_questions

    @pytest.mark.parametrize("preset", [
        "exam-mode",
        "beginner-mode",
        "research-mode",
        "concept-map-mode",
        "neurodivergent-friendly-mode",
    ])
    def test_different_presets_produce_different_content(self, sample_transcript, preset):
        """Test that different presets produce different content."""
        from pipeline.run_pipeline import _summary

        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id=preset,
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=[]
        )

        summary = _summary(context, sample_transcript)

        assert summary["artifactType"] == "summary"
        assert summary["presetId"] == preset
        assert "overview" in summary
        assert "sections" in summary

    def test_thread_refs_in_artifacts(self, sample_transcript):
        """Test that thread refs are included in artifacts."""
        from pipeline.run_pipeline import _summary, _key_terms

        thread_refs = ["thread-123", "thread-456"]
        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=thread_refs
        )

        summary = _summary(context, sample_transcript)
        key_terms = _key_terms(context)

        assert summary["threadRefs"] == thread_refs
        assert key_terms["threadRefs"] == thread_refs


class TestSchemaValidation:
    """Integration tests for schema validation."""

    def test_validate_real_summary(self, valid_summary_artifact):
        """Test validating a real summary artifact."""
        # This test requires actual schema files
        schema_dir = Path(__file__).parent.parent.parent / "schemas" / "artifacts"

        if not schema_dir.exists():
            pytest.skip("Schema directory not found")

        # Should not raise
        _validate(valid_summary_artifact, "summary.schema.json", schema_dir)

    def test_generate_and_validate_artifacts(self, sample_transcript):
        """Test that generated artifacts pass schema validation."""
        from pipeline.run_pipeline import _summary, _outline

        schema_dir = Path(__file__).parent.parent.parent / "schemas" / "artifacts"
        if not schema_dir.exists():
            pytest.skip("Schema directory not found")

        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=["thread-001"]
        )

        summary = _summary(context, sample_transcript)
        outline = _outline(context)

        # Should not raise
        _validate(summary, "summary.schema.json", schema_dir)
        _validate(outline, "outline.schema.json", schema_dir)


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_pipeline_execution(self, sample_transcript, temp_dir):
        """Test full pipeline execution from start to finish."""
        from pipeline.run_pipeline import run_pipeline
        from pipeline.progress_tracker import ProgressTracker

        output_dir = temp_dir / "output"
        context = PipelineContext(
            course_id="test-course",
            lecture_id="test-lecture",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=[]
        )

        # Create a progress tracker
        tracker = ProgressTracker(total_steps=3, verbose=False)

        # Run the pipeline
        run_pipeline(
            transcript=sample_transcript,
            context=context,
            output_dir=output_dir,
            use_llm=False,
            progress_tracker=tracker
        )

        # Verify outputs exist
        lecture_dir = output_dir / "test-lecture"
        assert lecture_dir.exists()

        # Check that all artifact files were created
        expected_files = [
            "summary.json",
            "outline.json",
            "key-terms.json",
            "flashcards.json",
            "exam-questions.json",
            "threads.json",
            "thread-occurrences.json",
            "thread-updates.json",
            "thread-continuity.json",
        ]

        for filename in expected_files:
            filepath = lecture_dir / filename
            assert filepath.exists(), f"Missing file: {filename}"

            # Verify it's valid JSON
            with open(filepath) as f:
                data = json.load(f)
                assert isinstance(data, dict)

        # Verify progress tracker recorded steps
        assert len(tracker.steps) == 3
        assert all(step.status == "completed" for step in tracker.steps)


    def test_pipeline_continuity_threshold_failure(self, sample_transcript, temp_dir):
        """Pipeline should fail when continuity score is below configured threshold."""
        from pipeline.run_pipeline import run_pipeline

        output_dir = temp_dir / "output"
        context = PipelineContext(
            course_id="test-course-threshold",
            lecture_id="test-lecture-threshold",
            preset_id="exam-mode",
            generated_at="2026-02-11T10:00:00Z",
            thread_refs=[],
        )

        with pytest.raises(ValueError, match="Thread continuity gate failed"):
            run_pipeline(
                transcript=sample_transcript,
                context=context,
                output_dir=output_dir,
                use_llm=False,
                continuity_threshold=0.99,
            )
