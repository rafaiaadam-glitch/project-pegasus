from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List


def _load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown_from_artifacts(artifacts: Dict[str, Dict]) -> str:
    summary = artifacts["summary"]
    outline = artifacts["outline"]
    key_terms = artifacts["key-terms"]
    flashcards = artifacts["flashcards"]
    questions = artifacts["exam-questions"]

    lines: List[str] = [
        f"# Lecture {summary.get('lectureId')}",
        "",
        "## Summary",
        summary.get("overview", ""),
        "",
    ]
    for section in summary.get("sections", []):
        lines.append(f"### {section.get('title')}")
        for bullet in section.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")

    lines.extend(["## Outline", ""])
    for node in outline.get("outline", []):
        lines.append(f"- **{node.get('title')}**")
        for point in node.get("points", []):
            lines.append(f"  - {point}")
        for child in node.get("children", []):
            lines.append(f"  - {child.get('title')}")
            for point in child.get("points", []):
                lines.append(f"    - {point}")
    lines.append("")

    lines.extend(["## Key Terms", ""])
    for term in key_terms.get("terms", []):
        lines.append(f"- **{term.get('term')}**: {term.get('definition')}")
    lines.append("")

    lines.extend(["## Flashcards", ""])
    for card in flashcards.get("cards", []):
        lines.append(f"- Q: {card.get('front')}")
        lines.append(f"  - A: {card.get('back')}")
    lines.append("")

    lines.extend(["## Exam Questions", ""])
    for question in questions.get("questions", []):
        lines.append(f"- {question.get('prompt')}")
        lines.append(f"  - Answer: {question.get('answer')}")
    lines.append("")

    return "\n".join(lines)


def _write_anki_csv(cards: List[Dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["front", "back", "tags"])
        for card in cards:
            tags = " ".join(card.get("tags", []))
            writer.writerow([card.get("front"), card.get("back"), tags])


def _write_pdf(text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = text.splitlines()
    y_start = 760
    line_height = 14

    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content_lines = ["BT", "/F1 11 Tf", f"72 {y_start} Td"]
    for line in lines:
        content_lines.append(f"({escape(line)}) Tj")
        content_lines.append(f"0 -{line_height} Td")
    content_lines.append("ET")
    content = "\n".join(content_lines)

    objects = []
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    objects.append(
        f"4 0 obj\n<< /Length {len(content.encode('utf-8'))} >>\nstream\n{content}\nendstream\nendobj\n"
    )
    objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    xref_offsets = []
    output = ["%PDF-1.4\n"]
    for obj in objects:
        xref_offsets.append(sum(len(part.encode("utf-8")) for part in output))
        output.append(obj)
    xref_start = sum(len(part.encode("utf-8")) for part in output)
    output.append("xref\n0 6\n0000000000 65535 f \n")
    for offset in xref_offsets:
        output.append(f"{offset:010} 00000 n \n")
    output.append(
        "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        f"{xref_start}\n%%EOF\n"
    )

    output_path.write_text("".join(output), encoding="utf-8")


def export_artifacts(lecture_id: str, artifact_dir: Path, export_dir: Path) -> None:
    artifacts = {
        "summary": _load_json(artifact_dir / "summary.json"),
        "outline": _load_json(artifact_dir / "outline.json"),
        "key-terms": _load_json(artifact_dir / "key-terms.json"),
        "flashcards": _load_json(artifact_dir / "flashcards.json"),
        "exam-questions": _load_json(artifact_dir / "exam-questions.json"),
    }

    markdown = _markdown_from_artifacts(artifacts)
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / f"{lecture_id}.md").write_text(markdown, encoding="utf-8")
    _write_anki_csv(artifacts["flashcards"].get("cards", []), export_dir / f"{lecture_id}.csv")
    _write_pdf(markdown, export_dir / f"{lecture_id}.pdf")
