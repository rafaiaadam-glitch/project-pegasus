from __future__ import annotations

import json
import pytest
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.jobs as jobs_module


class FakeDB:
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}
        self.lectures: dict[str, dict] = {}

    def create_job(self, payload: dict) -> None:
        self.jobs[payload["id"]] = payload

    def update_job(self, job_id: str, status=None, result=None, error=None, updated_at=None) -> None:
        job = self.jobs[job_id]
        if status is not None:
            job["status"] = status
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        if updated_at is not None:
            job["updated_at"] = updated_at

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def upsert_lecture(self, payload: dict) -> None:
        self.lectures[payload["id"]] = payload


def test_transcription_uses_metadata_when_lecture_missing(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage"
    (storage_dir / "audio").mkdir(parents=True, exist_ok=True)
    (storage_dir / "metadata").mkdir(parents=True, exist_ok=True)
    audio_path = storage_dir / "audio" / "lecture-abc.mp3"
    audio_path.write_bytes(b"audio")

    metadata = {
        "id": "lecture-abc",
        "courseId": "course-from-metadata",
        "presetId": "exam-mode",
        "title": "Metadata Lecture",
        "audioSource": {"storagePath": "storage/audio/lecture-abc.mp3"},
        "createdAt": "2024-03-10T00:00:00Z",
    }
    (storage_dir / "metadata" / "lecture-abc.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )

    fake_db = FakeDB()
    fake_db.create_job(
        {
            "id": "job-1",
            "lecture_id": "lecture-abc",
            "job_type": "transcription",
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": "2024-03-10T00:00:00Z",
            "updated_at": "2024-03-10T00:00:00Z",
        }
    )

    class StubWhisperModel:
        def transcribe(self, _path: str):
            return {
                "language": "en",
                "text": "Sample transcript.",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Sample transcript."}],
            }

    class StubWhisper:
        def load_model(self, _model: str):
            return StubWhisperModel()

    def fake_save_transcript(payload: str, name: str) -> str:
        out = storage_dir / "transcripts"
        out.mkdir(parents=True, exist_ok=True)
        target = out / name
        target.write_text(payload, encoding="utf-8")
        return str(target)

    monkeypatch.setenv("PLC_STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(jobs_module, "_load_whisper", lambda: StubWhisper())
    monkeypatch.setattr(jobs_module, "save_transcript", fake_save_transcript)

    jobs_module.run_transcription_job("job-1", "lecture-abc", "base")

    lecture = fake_db.fetch_lecture("lecture-abc")
    assert lecture is not None
    assert lecture["course_id"] == "course-from-metadata"
    assert lecture["preset_id"] == "exam-mode"
    assert lecture["title"] == "Metadata Lecture"
    assert lecture["audio_path"] == "storage/audio/lecture-abc.mp3"
    assert lecture["status"] == "transcribed"


def test_enqueue_job_runs_inline_when_configured(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.setenv("PLC_INLINE_JOBS", "true")

    def stub_task(job_id: str, value: str):
        jobs_module._update_job(job_id, "running")
        jobs_module._update_job(job_id, "completed", result={"value": value})

    job_id = jobs_module.enqueue_job("stub", "lecture-1", stub_task, "ok")

    job = fake_db.jobs[job_id]
    assert job["status"] == "completed"
    assert job["result"] == {"value": "ok"}


def test_enqueue_job_falls_back_to_inline_when_queue_unavailable(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.delenv("PLC_INLINE_JOBS", raising=False)

    def broken_queue():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(jobs_module, "_get_queue", broken_queue)

    def stub_task(job_id: str, value: str):
        jobs_module._update_job(job_id, "running")
        jobs_module._update_job(job_id, "completed", result={"value": value})

    job_id = jobs_module.enqueue_job("stub", "lecture-2", stub_task, "fallback")

    job = fake_db.jobs[job_id]
    assert job["status"] == "completed"
    assert job["result"] == {"value": "fallback"}


def test_enqueue_job_marks_failed_if_inline_task_raises(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.setenv("PLC_INLINE_JOBS", "1")

    def bad_task(job_id: str):
        jobs_module._update_job(job_id, "running")
        raise ValueError("boom")

    jobs_module.enqueue_job("stub", "lecture-3", bad_task)

    job = next(iter(fake_db.jobs.values()))
    assert job["status"] == "failed"
    assert "boom" in (job.get("error") or "")


def test_resolve_thread_refs_uses_course_threads_when_available():
    class FakeThreadDB:
        def fetch_threads_for_course(self, _course_id: str):
            return [
                {"id": "thread-1"},
                {"id": "thread-2"},
                {"id": ""},
                {"id": None},
                {},
            ]

    refs = jobs_module._resolve_thread_refs(FakeThreadDB(), "course-1")

    assert refs == ["thread-1", "thread-2"]


def test_resolve_thread_refs_returns_empty_when_method_missing():
    refs = jobs_module._resolve_thread_refs(object(), "course-1")

    assert refs == []


def test_generation_job_passes_existing_thread_refs_to_pipeline(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage"
    (storage_dir / "transcripts").mkdir(parents=True, exist_ok=True)
    (storage_dir / "transcripts" / "lecture-xyz.json").write_text(
        json.dumps({"text": "Transcript text."}), encoding="utf-8"
    )

    class FakeGenerationDB:
        def __init__(self) -> None:
            self.job_updates: list[tuple[str, str]] = []
            self.courses: list[dict] = []

        def update_job(self, job_id: str, status=None, result=None, error=None, updated_at=None):
            if status is not None:
                self.job_updates.append((job_id, status))

        def fetch_threads_for_course(self, _course_id: str):
            return [{"id": "thread-a"}, {"id": "thread-b"}]

        def upsert_course(self, payload: dict) -> None:
            self.courses.append(payload)

        def upsert_artifact(self, payload: dict) -> None:
            return None

        def upsert_thread(self, payload: dict) -> None:
            return None

    fake_db = FakeGenerationDB()
    observed = {}

    def fake_run_pipeline(transcript_text, context, output_dir, use_llm=False, openai_model="", llm_provider="openai", llm_model=None):
        observed["transcript_text"] = transcript_text
        observed["thread_refs"] = context.thread_refs
        observed["lecture_id"] = context.lecture_id

    monkeypatch.setenv("PLC_STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(jobs_module, "run_pipeline", fake_run_pipeline)

    result = jobs_module.run_generation_job(
        "job-4",
        lecture_id="lecture-xyz",
        course_id="course-123",
        preset_id="exam-mode",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )

    assert observed["transcript_text"] == "Transcript text."
    assert observed["thread_refs"] == ["thread-a", "thread-b"]
    assert observed["lecture_id"] == "lecture-xyz"
    assert fake_db.job_updates[0] == ("job-4", "running")
    assert fake_db.job_updates[-1] == ("job-4", "completed")
    assert result["lectureId"] == "lecture-xyz"


def test_resolve_thread_refs_deduplicates_and_normalizes_ids():
    class FakeThreadDB:
        def fetch_threads_for_course(self, _course_id: str):
            return [
                {"id": "thread-1"},
                {"id": " thread-1 "},
                {"id": "thread-2"},
            ]

    refs = jobs_module._resolve_thread_refs(FakeThreadDB(), "course-1")

    assert refs == ["thread-1", "thread-2"]


def test_resolve_thread_refs_returns_empty_on_db_error():
    class BrokenThreadDB:
        def fetch_threads_for_course(self, _course_id: str):
            raise RuntimeError("db unavailable")

    refs = jobs_module._resolve_thread_refs(BrokenThreadDB(), "course-1")

    assert refs == []


def test_resolve_thread_refs_returns_empty_when_not_list():
    class NonListThreadDB:
        def fetch_threads_for_course(self, _course_id: str):
            return {"id": "thread-1"}

    refs = jobs_module._resolve_thread_refs(NonListThreadDB(), "course-1")

    assert refs == []


def test_log_job_event_emits_structured_fields(monkeypatch):
    class FakeLogger:
        def __init__(self):
            self.calls = []

        def info(self, event, extra=None):
            self.calls.append((event, extra))

    fake_logger = FakeLogger()
    monkeypatch.setattr(jobs_module, "LOGGER", fake_logger)

    jobs_module._log_job_event(
        "job.updated",
        job_id="job-1",
        lecture_id="lecture-1",
        status="running",
        error=None,
    )

    assert fake_logger.calls == [
        (
            "job.updated",
            {"job_id": "job-1", "lecture_id": "lecture-1", "status": "running"},
        )
    ]


def test_create_and_update_job_record_logs(monkeypatch):
    class FakeLogger:
        def __init__(self):
            self.calls = []

        def info(self, event, extra=None):
            self.calls.append((event, extra))

    fake_db = FakeDB()
    fake_logger = FakeLogger()
    monkeypatch.setattr(jobs_module, "LOGGER", fake_logger)
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)

    jobs_module._create_job_record("job-logger", "export", "lecture-logger")
    jobs_module._update_job("job-logger", "running")

    created_event, created_fields = fake_logger.calls[0]
    updated_event, updated_fields = fake_logger.calls[1]

    assert created_event == "job.created"
    assert created_fields["job_id"] == "job-logger"
    assert created_fields["lecture_id"] == "lecture-logger"
    assert created_fields["job_type"] == "export"
    assert created_fields["status"] == "queued"

    assert updated_event == "job.updated"
    assert updated_fields["job_id"] == "job-logger"
    assert updated_fields["status"] == "running"



def test_assert_minimum_artifact_quality_passes_with_required_artifacts():
    class FakeExportDB:
        def fetch_artifacts(self, _lecture_id: str):
            return [
                {"artifact_type": "summary", "summary_section_count": 3, "summary_overview": "Overview"},
                {"artifact_type": "outline"},
                {"artifact_type": "key-terms"},
                {"artifact_type": "flashcards"},
                {"artifact_type": "exam-questions"},
            ]

    jobs_module._assert_minimum_artifact_quality(FakeExportDB(), "lecture-1")


def test_assert_minimum_artifact_quality_fails_when_artifacts_missing():
    class FakeExportDB:
        def fetch_artifacts(self, _lecture_id: str):
            return [{"artifact_type": "summary", "summary_section_count": 3, "summary_overview": "Overview"}]

    with pytest.raises(ValueError, match="required artifacts"):
        jobs_module._assert_minimum_artifact_quality(FakeExportDB(), "lecture-1")


def test_assert_minimum_artifact_quality_fails_for_low_summary_sections(monkeypatch):
    class FakeExportDB:
        def fetch_artifacts(self, _lecture_id: str):
            return [
                {"artifact_type": "summary", "summary_section_count": 1, "summary_overview": "Overview"},
                {"artifact_type": "outline"},
                {"artifact_type": "key-terms"},
                {"artifact_type": "flashcards"},
                {"artifact_type": "exam-questions"},
            ]

    monkeypatch.setenv("PLC_EXPORT_MIN_SUMMARY_SECTIONS", "2")
    with pytest.raises(ValueError, match="requires >= 2 sections"):
        jobs_module._assert_minimum_artifact_quality(FakeExportDB(), "lecture-1")


def test_assert_minimum_artifact_quality_fails_for_empty_summary_overview():
    class FakeExportDB:
        def fetch_artifacts(self, _lecture_id: str):
            return [
                {"artifact_type": "summary", "summary_section_count": 3, "summary_overview": "   "},
                {"artifact_type": "outline"},
                {"artifact_type": "key-terms"},
                {"artifact_type": "flashcards"},
                {"artifact_type": "exam-questions"},
            ]

    with pytest.raises(ValueError, match="overview is empty"):
        jobs_module._assert_minimum_artifact_quality(FakeExportDB(), "lecture-1")


def test_google_speech_transcription_success(monkeypatch, tmp_path):
    """Test successful Google Speech-to-Text transcription"""
    from unittest.mock import Mock, MagicMock

    # Create mock response structure
    mock_alternative = Mock()
    mock_alternative.transcript = "Hello world"

    mock_result1 = Mock()
    mock_result1.alternatives = [mock_alternative]

    mock_alternative2 = Mock()
    mock_alternative2.transcript = "This is a test"

    mock_result2 = Mock()
    mock_result2.alternatives = [mock_alternative2]

    mock_alternative3 = Mock()
    mock_alternative3.transcript = "Google Speech API"

    mock_result3 = Mock()
    mock_result3.alternatives = [mock_alternative3]

    mock_response = Mock()
    mock_response.results = [mock_result1, mock_result2, mock_result3]

    # Create mock client
    mock_client = Mock()
    mock_client.recognize.return_value = mock_response

    # Mock the entire google.cloud.speech_v1 module
    mock_speech = MagicMock()
    mock_speech.SpeechClient.return_value = mock_client
    mock_speech.RecognitionAudio = Mock
    mock_speech.RecognitionConfig = Mock

    # Patch the import
    monkeypatch.setattr("backend.jobs.speech_v1", mock_speech, raising=False)

    # Also need to mock the import itself
    import sys
    sys.modules['google.cloud.speech_v1'] = mock_speech

    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio data")

    result = jobs_module._transcribe_with_google_speech(audio_path, "en-US")

    assert result["language"] == "en-US"
    assert result["text"] == "Hello world This is a test Google Speech API"
    assert len(result["segments"]) == 3
    assert result["segments"][0]["text"] == "Hello world"
    assert result["segments"][1]["text"] == "This is a test"
    assert result["segments"][2]["text"] == "Google Speech API"
    assert result["engine"]["provider"] == "google_speech"
    assert result["engine"]["model"] == "latest_long"

    # Check that segments have timing
    assert result["segments"][0]["startSec"] == 0.0
    assert result["segments"][0]["endSec"] > 0.0
    assert result["segments"][1]["startSec"] > 0.0


def test_google_speech_uses_env_language_code(monkeypatch, tmp_path):
    """Test that Google STT uses PLC_STT_LANGUAGE env var when language_code is None"""
    from unittest.mock import Mock, MagicMock

    # Create mock response
    mock_alternative = Mock()
    mock_alternative.transcript = "Test transcript"

    mock_result = Mock()
    mock_result.alternatives = [mock_alternative]

    mock_response = Mock()
    mock_response.results = [mock_result]

    # Create mock client
    mock_client = Mock()
    mock_client.recognize.return_value = mock_response

    # Mock the module
    mock_speech = MagicMock()
    mock_speech.SpeechClient.return_value = mock_client
    mock_speech.RecognitionAudio = Mock
    mock_speech.RecognitionConfig = Mock

    import sys
    sys.modules['google.cloud.speech_v1'] = mock_speech

    monkeypatch.setenv("PLC_STT_LANGUAGE", "es-ES")
    monkeypatch.setenv("PLC_GCP_STT_MODEL", "latest_short")

    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio data")

    result = jobs_module._transcribe_with_google_speech(audio_path, None)

    assert result["language"] == "es-ES"
    assert result["engine"]["model"] == "latest_short"


def test_google_speech_handles_empty_alternatives(monkeypatch, tmp_path):
    """Test that Google STT skips results with no alternatives or empty text"""
    from unittest.mock import Mock, MagicMock

    # Create mock results with various edge cases
    mock_alt1 = Mock()
    mock_alt1.transcript = "Valid text"

    mock_result1 = Mock()
    mock_result1.alternatives = [mock_alt1]

    mock_result2 = Mock()
    mock_result2.alternatives = []  # No alternatives

    mock_alt3 = Mock()
    mock_alt3.transcript = "   "  # Whitespace only

    mock_result3 = Mock()
    mock_result3.alternatives = [mock_alt3]

    mock_alt4 = Mock()
    mock_alt4.transcript = "Another valid text"

    mock_result4 = Mock()
    mock_result4.alternatives = [mock_alt4]

    mock_response = Mock()
    mock_response.results = [mock_result1, mock_result2, mock_result3, mock_result4]

    # Create mock client
    mock_client = Mock()
    mock_client.recognize.return_value = mock_response

    # Mock the module
    mock_speech = MagicMock()
    mock_speech.SpeechClient.return_value = mock_client
    mock_speech.RecognitionAudio = Mock
    mock_speech.RecognitionConfig = Mock

    import sys
    sys.modules['google.cloud.speech_v1'] = mock_speech

    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio data")

    result = jobs_module._transcribe_with_google_speech(audio_path, "en-US")

    # Should only have 2 valid segments
    assert len(result["segments"]) == 2
    assert result["segments"][0]["text"] == "Valid text"
    assert result["segments"][1]["text"] == "Another valid text"
    assert result["text"] == "Valid text Another valid text"


def test_google_speech_raises_on_missing_library(monkeypatch, tmp_path):
    """Test that missing google-cloud-speech raises helpful error"""
    from unittest.mock import patch

    import sys
    # Remove module if it exists
    if 'google.cloud.speech_v1' in sys.modules:
        del sys.modules['google.cloud.speech_v1']
    if 'google.cloud' in sys.modules:
        del sys.modules['google.cloud']
    if 'google' in sys.modules:
        del sys.modules['google']

    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio data")

    # Mock the import to raise ImportError
    def mock_import(name, *args, **kwargs):
        if 'google.cloud' in name:
            raise ImportError(f"No module named '{name}'")
        return __import__(name, *args, **kwargs)

    with patch('builtins.__import__', side_effect=mock_import):
        with pytest.raises(RuntimeError, match="google-cloud-speech is required"):
            jobs_module._transcribe_with_google_speech(audio_path, "en-US")
