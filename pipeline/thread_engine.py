"""
Thread Engine — Pegasus Lecture Copilot

Detects concepts in a lecture transcript and tracks how they evolve across
lectures within a course.

Detection strategy:
  - If OPENAI_API_KEY is set: uses OpenAI to identify real academic concepts
    and classify change types (refinement / contradiction / complexity).
  - Fallback: lightweight multi-word term extraction (no LLM required).

All outputs are validated against the project schemas before being returned.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.request


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STOPWORDS = {
    # Articles / prepositions / conjunctions
    "the", "and", "for", "with", "that", "this", "from", "into", "than",
    "then", "about", "which", "when", "what", "where", "while", "also",
    "such", "over", "all", "any", "via", "per", "by", "as", "or", "if",
    "so", "up", "in", "on", "at", "to", "of", "a", "an",
    # Pronouns
    "their", "your", "they", "them", "we", "he", "she", "him", "her",
    "its", "his", "you", "our", "me", "my", "it", "i",
    # Common verbs / auxiliaries
    "are", "was", "were", "have", "has", "had", "been", "being", "be",
    "is", "do", "will", "can", "may", "not", "but", "use", "using", "used",
    "more", "most", "some", "out", "no",
    # Generic filler words that are never academic concepts
    "today", "covered", "cover", "discussed", "discuss", "introduced",
    "introduce", "lecture", "class", "topic", "course", "section",
    "chapter", "let", "now", "first", "second", "third", "next", "last",
    "also", "well", "just", "very", "much", "many", "however", "therefore",
    "furthermore", "finally", "example", "note", "see", "look", "think",
    "know", "show", "shows", "shown", "means", "mean", "called", "known",
    "understand", "understanding", "important", "different", "same",
    "between", "through", "during", "within", "without", "each", "both",
    "these", "those", "other", "another", "given", "related", "based",
}

VALID_CHANGE_TYPES = {"refinement", "contradiction", "complexity"}
VALID_STATUSES = {"foundational", "advanced"}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sentence_for_term(transcript: str, term: str) -> str:
    """Return the first sentence in the transcript that contains the term."""
    sentences = re.split(r"(?<=[.!?])\s+", transcript)
    term_lower = term.lower()
    for sentence in sentences:
        if term_lower in sentence.lower():
            return sentence.strip()
    # Fallback: return a short excerpt around the first occurrence
    idx = transcript.lower().find(term_lower)
    if idx == -1:
        return transcript[:120].strip()
    start = max(0, idx - 40)
    end = min(len(transcript), idx + 120)
    return transcript[start:end].strip()


def _top_terms(transcript: str, top_n: int = 8) -> List[Tuple[str, int]]:
    """
    Lightweight fallback: extract frequent multi-word noun phrases and
    single content words from the transcript.
    """
    text = transcript.lower()

    # Extract 2-word phrases first (more concept-like)
    bigrams: Dict[str, int] = {}
    words = re.findall(r"\b[a-z][a-z\-]{2,}\b", text)
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        if w1 not in STOPWORDS and w2 not in STOPWORDS:
            phrase = f"{w1} {w2}"
            bigrams[phrase] = bigrams.get(phrase, 0) + 1

    # Single content words as fallback
    unigrams: Dict[str, int] = {}
    for word in words:
        if word not in STOPWORDS and len(word) > 5:
            unigrams[word] = unigrams.get(word, 0) + 1

    # Prefer bigrams that appear more than once
    candidates = {k: v for k, v in bigrams.items() if v > 1}
    # Fill remaining slots with top unigrams
    sorted_uni = sorted(unigrams.items(), key=lambda x: x[1], reverse=True)
    for word, count in sorted_uni:
        if len(candidates) >= top_n:
            break
        # Skip if word is already part of a bigram candidate
        already_covered = any(word in phrase for phrase in candidates)
        if not already_covered:
            candidates[word] = count

    return sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:top_n]


# ---------------------------------------------------------------------------
# ThreadStore — persists threads per course to local disk
# ---------------------------------------------------------------------------

class ThreadStore:
    """Loads and saves thread records for a course from/to a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Dict[str, Dict[str, Any]]:
        """Return a dict of thread_id → thread record."""
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return {}
            return {t["id"]: t for t in raw if isinstance(t, dict) and "id" in t}
        except (OSError, json.JSONDecodeError, KeyError):
            return {}

    def save(self, threads: List[Dict[str, Any]]) -> None:
        """Persist the full list of threads for this course."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(threads, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# OpenAI concept detection
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the Thread Engine for Pegasus Lecture Copilot.

Your job is to analyse a university lecture transcript and identify academic
concepts that should be tracked across lectures in this course.

You will be given:
1. The lecture transcript.
2. A list of concepts (threads) already tracked for this course.

Return STRICT JSON only — no markdown, no explanation.

Return an object with two keys:

"new_concepts": array of objects, one per brand-new concept not in the existing
threads list. Each object:
  {
    "title": "<concept name, title-cased, concise>",
    "summary": "<one sentence: what this concept is>",
    "evidence": "<direct quote or close paraphrase from the transcript, max 160 chars>",
    "complexity_level": <integer 1–5, 1=introductory>,
    "status": "<foundational|advanced>"
  }

"concept_updates": array of objects, one per existing concept that appears in
this lecture. Each object:
  {
    "title": "<must exactly match a title from existing_threads>",
    "change_type": "<refinement|contradiction|complexity>",
    "summary": "<one sentence describing what changed>",
    "evidence": "<direct quote or close paraphrase from the transcript, max 160 chars>",
    "new_complexity_level": <integer 1–5, or null if unchanged>
  }

Rules:
- Only return concepts that genuinely appear in the transcript.
- "contradiction" means the lecture presents a conflicting claim to what was
  previously summarised for that thread.
- "complexity" means the concept is being treated at a significantly deeper
  level than before (increase new_complexity_level accordingly).
- "refinement" means the concept is revisited with more detail or nuance.
- Return an empty array if there are no new concepts or no updates.
- Keep concept titles concise (2–5 words where possible).
- Do NOT hallucinate content not present in the transcript.
"""


def _call_openai(
    transcript: str,
    existing_threads: List[Dict[str, Any]],
    model: str,
) -> Dict[str, Any]:
    """Call OpenAI and return parsed JSON response."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    existing_summary = [
        {"title": t["title"], "summary": t["summary"]}
        for t in existing_threads
    ]

    user_content = (
        f"existing_threads: {json.dumps(existing_summary)}\n\n"
        f"transcript:\n{transcript}"
    )

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    # Extract text from OpenAI responses API format
    for output in raw.get("output", []):
        for content in output.get("content", []):
            if "text" in content:
                return json.loads(content["text"])

    raise ValueError("OpenAI response did not contain extractable JSON text.")


def _safe_change_type(value: Any) -> str:
    if isinstance(value, str) and value in VALID_CHANGE_TYPES:
        return value
    return "refinement"


def _safe_status(value: Any) -> str:
    if isinstance(value, str) and value in VALID_STATUSES:
        return value
    return "foundational"


def _clamp_complexity(value: Any, current: int = 1) -> int:
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    return current


# ---------------------------------------------------------------------------
# Core: build thread / occurrence / update records from OpenAI output
# ---------------------------------------------------------------------------

def _process_llm_output(
    llm_result: Dict[str, Any],
    existing: Dict[str, Dict[str, Any]],
    course_id: str,
    lecture_id: str,
    generated_at: str,
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    threads: List[Dict[str, Any]] = list(existing.values())
    occurrences: List[Dict[str, Any]] = []
    updates: List[Dict[str, Any]] = []

    # --- New concepts ---
    for concept in llm_result.get("new_concepts", []):
        if not isinstance(concept, dict):
            continue
        title = str(concept.get("title", "")).strip()
        summary = str(concept.get("summary", "")).strip()
        evidence = str(concept.get("evidence", "")).strip()
        if not title or not summary:
            continue

        thread_id = str(uuid.uuid4())
        complexity = _clamp_complexity(concept.get("complexity_level"), 1)
        status = _safe_status(concept.get("status"))

        thread: Dict[str, Any] = {
            "id": thread_id,
            "courseId": course_id,
            "title": title,
            "summary": summary,
            "status": status,
            "complexityLevel": complexity,
            "lectureRefs": [lecture_id],
            "evolutionNotes": [
                {
                    "lectureId": lecture_id,
                    "changeType": "refinement",
                    "note": f"Concept first introduced in lecture {lecture_id}.",
                }
            ],
        }
        threads.append(thread)

        occurrences.append({
            "id": str(uuid.uuid4()),
            "threadId": thread_id,
            "courseId": course_id,
            "lectureId": lecture_id,
            "artifactId": "summary",
            "evidence": evidence[:180] or summary[:180],
            "confidence": 0.85,
            "capturedAt": generated_at,
        })

    # --- Updates to existing concepts ---
    existing_by_title = {t["title"]: t for t in threads}

    for update in llm_result.get("concept_updates", []):
        if not isinstance(update, dict):
            continue
        title = str(update.get("title", "")).strip()
        change_type = _safe_change_type(update.get("change_type"))
        summary_text = str(update.get("summary", "")).strip()
        evidence = str(update.get("evidence", "")).strip()

        if not title or not summary_text:
            continue

        matching = existing_by_title.get(title)
        if matching is None:
            continue

        thread_id = matching["id"]

        # Update lecture refs
        refs = matching.get("lectureRefs", [])
        if lecture_id not in refs:
            refs = sorted(set(refs + [lecture_id]))
        matching["lectureRefs"] = refs

        # Update complexity if provided
        new_complexity = update.get("new_complexity_level")
        if new_complexity is not None:
            matching["complexityLevel"] = _clamp_complexity(
                new_complexity, matching.get("complexityLevel", 1)
            )

        # Update status based on complexity
        if matching.get("complexityLevel", 1) > 2:
            matching["status"] = "advanced"

        # Update thread summary to reflect latest understanding
        matching["summary"] = summary_text

        # Append evolution note
        matching.setdefault("evolutionNotes", []).append({
            "lectureId": lecture_id,
            "changeType": change_type,
            "note": summary_text,
        })

        occurrences.append({
            "id": str(uuid.uuid4()),
            "threadId": thread_id,
            "courseId": course_id,
            "lectureId": lecture_id,
            "artifactId": "summary",
            "evidence": evidence[:180] or summary_text[:180],
            "confidence": 0.90,
            "capturedAt": generated_at,
        })

        updates.append({
            "id": str(uuid.uuid4()),
            "threadId": thread_id,
            "courseId": course_id,
            "lectureId": lecture_id,
            "changeType": change_type,
            "summary": summary_text,
            "details": [evidence[:140]] if evidence else [],
            "capturedAt": generated_at,
        })

    return threads, occurrences, updates


# ---------------------------------------------------------------------------
# Fallback: keyword-based detection (no LLM)
# ---------------------------------------------------------------------------

def _process_fallback(
    transcript: str,
    existing: Dict[str, Dict[str, Any]],
    course_id: str,
    lecture_id: str,
    generated_at: str,
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    threads: List[Dict[str, Any]] = list(existing.values())
    occurrences: List[Dict[str, Any]] = []
    updates: List[Dict[str, Any]] = []
    existing_titles = {t["title"].lower(): t for t in threads}

    for term, count in _top_terms(transcript):
        evidence = _sentence_for_term(transcript, term)
        title = term.title()
        title_lower = title.lower()

        matching = existing_titles.get(title_lower)

        if matching is None:
            thread_id = str(uuid.uuid4())
            thread: Dict[str, Any] = {
                "id": thread_id,
                "courseId": course_id,
                "title": title,
                "summary": f"Concept '{title}' identified in lecture {lecture_id}.",
                "status": "foundational",
                "complexityLevel": 1,
                "lectureRefs": [lecture_id],
                "evolutionNotes": [
                    {
                        "lectureId": lecture_id,
                        "changeType": "refinement",
                        "note": f"First appearance detected.",
                    }
                ],
            }
            threads.append(thread)
            existing_titles[title_lower] = thread
        else:
            thread_id = matching["id"]
            refs = matching.get("lectureRefs", [])
            if lecture_id not in refs:
                matching["lectureRefs"] = sorted(set(refs + [lecture_id]))
            matching.setdefault("evolutionNotes", []).append({
                "lectureId": lecture_id,
                "changeType": "refinement",
                "note": f"Concept revisited in lecture {lecture_id}.",
            })
            updates.append({
                "id": str(uuid.uuid4()),
                "threadId": thread_id,
                "courseId": course_id,
                "lectureId": lecture_id,
                "changeType": "refinement",
                "summary": f"'{title}' revisited.",
                "details": [evidence[:140]],
                "capturedAt": generated_at,
            })

        occurrences.append({
            "id": str(uuid.uuid4()),
            "threadId": thread_id,
            "courseId": course_id,
            "lectureId": lecture_id,
            "artifactId": "summary",
            "evidence": evidence[:180],
            "confidence": min(0.95, 0.5 + (count / 10)),
            "capturedAt": generated_at,
        })

    return threads, occurrences, updates


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_thread_records(
    course_id: str,
    lecture_id: str,
    transcript: str,
    generated_at: Optional[str],
    storage_dir: Path,
    openai_model: str = "gpt-4o-mini",
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """
    Analyse a transcript and return:
      (threads, thread_occurrences, thread_updates)

    Uses OpenAI if OPENAI_API_KEY is set, otherwise falls back to keyword
    extraction. All returned records conform to the project schemas.
    """
    if generated_at is None:
        generated_at = _iso_now()

    store = ThreadStore(storage_dir / "threads" / f"{course_id}.json")
    existing = store.load()
    existing_list = list(existing.values())

    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        try:
            llm_result = _call_openai(transcript, existing_list, openai_model)
            threads, occurrences, updates = _process_llm_output(
                llm_result, existing, course_id, lecture_id, generated_at
            )
        except Exception as exc:
            # Fail loudly as per engineering principles — do not silently accept
            # garbage, but do fall back gracefully with a clear warning so the
            # pipeline can continue producing other artifacts.
            print(
                f"[ThreadEngine] WARNING: OpenAI call failed ({exc}). "
                "Falling back to keyword detection."
            )
            threads, occurrences, updates = _process_fallback(
                transcript, existing, course_id, lecture_id, generated_at
            )
    else:
        threads, occurrences, updates = _process_fallback(
            transcript, existing, course_id, lecture_id, generated_at
        )

    store.save(threads)
    return threads, occurrences, updates
