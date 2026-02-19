from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


def test_extract_context_text_plain_text(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    content = b"Line one\nLine two"
    file_path.write_bytes(content)

    extracted = app_module._extract_context_text(
        file_path=file_path,
        content=content,
        content_type="text/plain",
    )

    assert extracted == "Line one\nLine two"


def test_extract_context_text_docx(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")

    file_path = tmp_path / "syllabus.docx"
    document = docx.Document()
    document.add_paragraph("Week 1: Introduction")
    document.add_paragraph("Week 2: Core concepts")
    document.save(file_path)

    extracted = app_module._extract_context_text(
        file_path=file_path,
        content=file_path.read_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert extracted == "Week 1: Introduction\nWeek 2: Core concepts"


def test_extract_context_text_docx_by_extension_when_content_type_is_generic(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")

    file_path = tmp_path / "notes.docx"
    document = docx.Document()
    document.add_paragraph("Content type can be unreliable")
    document.save(file_path)

    extracted = app_module._extract_context_text(
        file_path=file_path,
        content=file_path.read_bytes(),
        content_type="application/octet-stream",
    )

    assert extracted == "Content type can be unreliable"


def test_extract_context_text_docx_without_dependency_returns_placeholder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file_path = tmp_path / "fallback.docx"
    file_path.write_bytes(b"fake docx bytes")

    monkeypatch.setattr(app_module, "DOCX_AVAILABLE", False)

    extracted = app_module._extract_context_text(
        file_path=file_path,
        content=file_path.read_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert extracted == "[DOCX file: fallback.docx - install python-docx for text extraction]"
