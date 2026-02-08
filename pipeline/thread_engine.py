from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "are",
    "was",
    "were",
    "into",
    "than",
    "then",
    "their",
    "your",
    "they",
    "them",
    "about",
    "which",
    "when",
    "what",
    "where",
    "while",
    "also",
    "such",
    "over",
    "more",
    "most",
    "some",
    "have",
    "has",
    "had",
    "been",
    "being",
    "but",
    "not",
    "you",
    "our",
    "out",
    "all",
    "any",
    "can",
    "may",
    "will",
    "its",
    "his",
    "her",
    "she",
    "him",
    "our",
    "via",
    "per",
    "use",
    "using",
    "used",
}


@dataclass(frozen=True)
class ThreadStore:
    path: Path

    def load(self) -> Dict[str, Dict[str, object]]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return {item["id"]: item for item in data.get("threads", [])}

    def save(self, threads: Iterable[Dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"threads": list(threads)}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text.lower())
    return [token for token in tokens if token not in STOPWORDS]


def _top_terms(text: str, limit: int = 5) -> List[Tuple[str, int]]:
    counts = Counter(_tokenize(text))
    return counts.most_common(limit)


def _sentence_for_term(text: str, term: str) -> str:
    sentences = re.split(r"[.!?]\s+", text)
    for sentence in sentences:
        if term in sentence.lower():
            return sentence.strip()
    return sentences[0].strip() if sentences else term


def generate_thread_records(
    course_id: str,
    lecture_id: str,
    transcript: str,
    generated_at: str | None,
    storage_dir: Path,
) -> tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]]]:
    if generated_at is None:
        generated_at = _iso_now()

    store = ThreadStore(storage_dir / "threads" / f"{course_id}.json")
    existing = store.load()

    threads: List[Dict[str, object]] = list(existing.values())
    occurrences: List[Dict[str, object]] = []
    updates: List[Dict[str, object]] = []

    for term, count in _top_terms(transcript):
        matching = next(
            (thread for thread in threads if thread["title"] == term), None
        )
        evidence = _sentence_for_term(transcript, term)
        if matching is None:
            thread_id = str(uuid.uuid4())
            thread = {
                "id": thread_id,
                "courseId": course_id,
                "title": term,
                "summary": f"Lecture concept around '{term}'.",
                "status": "foundational" if count < 6 else "advanced",
                "complexityLevel": min(5, max(1, count // 2)),
                "lectureRefs": [lecture_id],
                "evolutionNotes": [
                    {
                        "lectureId": lecture_id,
                        "changeType": "refinement",
                        "note": f"Initial introduction of '{term}'.",
                    }
                ],
            }
            threads.append(thread)
        else:
            thread_id = matching["id"]
            lecture_refs = set(matching.get("lectureRefs", []))
            lecture_refs.add(lecture_id)
            matching["lectureRefs"] = sorted(lecture_refs)
            matching.setdefault("evolutionNotes", []).append(
                {
                    "lectureId": lecture_id,
                    "changeType": "refinement",
                    "note": f"Revisited '{term}' with added context.",
                }
            )
            updates.append(
                {
                    "id": str(uuid.uuid4()),
                    "threadId": thread_id,
                    "courseId": course_id,
                    "lectureId": lecture_id,
                    "changeType": "refinement",
                    "summary": f"Expanded '{term}' with new lecture context.",
                    "details": [evidence[:140]],
                    "capturedAt": generated_at,
                }
            )

        occurrences.append(
            {
                "id": str(uuid.uuid4()),
                "threadId": thread_id,
                "courseId": course_id,
                "lectureId": lecture_id,
                "artifactId": "summary",
                "evidence": evidence[:180],
                "confidence": min(0.95, 0.5 + (count / 10)),
                "capturedAt": generated_at,
            }
        )

    store.save(threads)
    if not updates:
        updates.append(
            {
                "id": str(uuid.uuid4()),
                "threadId": threads[0]["id"] if threads else str(uuid.uuid4()),
                "courseId": course_id,
                "lectureId": lecture_id,
                "changeType": "refinement",
                "summary": "Captured initial thread signals for this lecture.",
                "details": ["Generated from top lecture terms."],
                "capturedAt": generated_at,
            }
        )

    return threads, occurrences, updates
