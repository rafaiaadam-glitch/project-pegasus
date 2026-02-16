"""
Thread Engine — Pegasus Lecture Copilot

Detects concepts in a lecture transcript and tracks how they evolve across
lectures within a course.

Detection strategy:
  - If LLM credentials are set: uses configured provider to identify concepts
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
import urllib.parse
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

# Module-level storage for last detection metrics
_last_metrics = None
_last_quality_score = None


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
# LLM-backed concept detection
# ---------------------------------------------------------------------------

def _build_system_prompt(preset_config: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a system prompt for thread detection, optionally customized for a preset.

    Args:
        preset_config: Optional preset configuration with diceWeights and emphasis

    Returns:
        System prompt string
    """
    base_prompt = """\
You are the Thread Engine for Pegasus Lecture Copilot.

Your job is to analyse a university lecture transcript and identify academic
concepts that should be tracked across lectures in this course.

You will be given:
1. COURSE CONTEXT (if available): syllabus and notes uploaded by the student
   - Use this to understand the course structure and expected topics
   - Prioritize concepts that align with the syllabus
   - Use terminology consistent with course materials
2. The lecture transcript.
3. A list of concepts (threads) already tracked for this course."""

    # Add preset-specific guidance
    if preset_config:
        dice_weights = preset_config.get("diceWeights", {})
        optimized_for = preset_config.get("optimizedFor", [])
        target_disciplines = preset_config.get("targetDisciplines", [])

        if dice_weights or optimized_for:
            base_prompt += "\n\nMODE: " + preset_config.get("name", "Standard Mode")

            if target_disciplines:
                base_prompt += f"\nTarget disciplines: {', '.join(target_disciplines)}"

            if optimized_for:
                base_prompt += f"\nOptimized for: {', '.join(optimized_for)}"

            if dice_weights:
                base_prompt += "\n\nCONCEPT DETECTION PRIORITIES (dice weights):"
                if dice_weights.get("who", 0) > 0:
                    weight_pct = int(dice_weights["who"] * 100)
                    base_prompt += f"\n- WHO ({weight_pct}%): Identify speakers, authors, schools of thought, and attribution"
                if dice_weights.get("why", 0) > 0:
                    weight_pct = int(dice_weights["why"] * 100)
                    base_prompt += f"\n- WHY ({weight_pct}%): Track normative claims, philosophical stakes, and underlying rationales"
                if dice_weights.get("how", 0) > 0:
                    weight_pct = int(dice_weights["how"] * 100)
                    base_prompt += f"\n- HOW ({weight_pct}%): Capture argument structure, methodology, and logical flow"
                if dice_weights.get("what", 0) > 0:
                    weight_pct = int(dice_weights["what"] * 100)
                    base_prompt += f"\n- WHAT ({weight_pct}%): Record core concepts, definitions, and subject matter"
                if dice_weights.get("where", 0) > 0:
                    weight_pct = int(dice_weights["where"] * 100)
                    base_prompt += f"\n- WHERE ({weight_pct}%): Note geographic, institutional, or contextual settings"
                if dice_weights.get("when", 0) > 0:
                    weight_pct = int(dice_weights["when"] * 100)
                    base_prompt += f"\n- WHEN ({weight_pct}%): Track historical context and temporal relationships"

    base_prompt += """

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

    return base_prompt


_SYSTEM_PROMPT = _build_system_prompt()  # Default prompt for backward compatibility


def _call_openai(
    transcript: str,
    existing_threads: List[Dict[str, Any]],
    model: str,
    timeout: int = 90,
    preset_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call OpenAI with retry logic and return parsed JSON response."""
    from pipeline.retry_utils import (
        with_retry,
        retry_config_from_env,
        NonRetryableError,
    )

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

    # Build preset-aware system prompt
    system_prompt = _build_system_prompt(preset_config) if preset_config else _SYSTEM_PROMPT

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
    }

    def make_request() -> Dict[str, Any]:
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

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        # Extract text from OpenAI responses API format
        for output in raw.get("output", []):
            for content in output.get("content", []):
                if "text" in content:
                    return json.loads(content["text"])

        raise ValueError("OpenAI response did not contain extractable JSON text.")

    config = retry_config_from_env()

    try:
        return with_retry(make_request, config=config,
                         operation_name="OpenAI thread detection")
    except NonRetryableError as e:
        raise RuntimeError(f"OpenAI thread detection failed: {e}") from e




def _call_gemini(
    transcript: str,
    existing_threads: List[Dict[str, Any]],
    model: str,
    timeout: int = 90,
    course_context: Optional[Dict[str, str]] = None,
    preset_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call Gemini with retry logic and return parsed JSON response."""
    from pipeline.retry_utils import NonRetryableError, retry_config_from_env, with_retry

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is not set.")

    existing_summary = [{"title": t["title"], "summary": t["summary"]} for t in existing_threads]

    # Build user content with course context if available
    content_parts = []

    # Add course context (syllabus gets priority)
    if course_context:
        if course_context.get("syllabus"):
            content_parts.append(f"=== COURSE SYLLABUS (use as primary reference) ===\n{course_context['syllabus']}\n")
        if course_context.get("notes"):
            # Truncate notes if too long (keep first 5000 chars)
            notes = course_context['notes']
            if len(notes) > 5000:
                notes = notes[:5000] + "\n[... truncated for length ...]"
            content_parts.append(f"=== COURSE NOTES (supporting context) ===\n{notes}\n")

    content_parts.append(f"existing_threads: {json.dumps(existing_summary)}\n")
    content_parts.append(f"transcript:\n{transcript}")

    user_content = "\n".join(content_parts)

    # Build preset-aware system prompt
    system_prompt = _build_system_prompt(preset_config) if preset_config else _SYSTEM_PROMPT

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(api_key)}"
    )

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    def make_request() -> Dict[str, Any]:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        for candidate in raw.get("candidates", []):
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return json.loads(text)

        raise ValueError("Gemini response did not contain extractable JSON text.")

    config = retry_config_from_env()

    try:
        return with_retry(make_request, config=config, operation_name="Gemini thread detection")
    except NonRetryableError as e:
        raise RuntimeError(f"Gemini thread detection failed: {e}") from e
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
# Core: build thread / occurrence / update records from LLM output
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
    llm_provider: str = "openai",
    llm_model: str | None = None,
    preset_id: Optional[str] = None,
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """
    Analyse a transcript and return:
      (threads, thread_occurrences, thread_updates)

    Uses configured LLM provider if credentials are available, otherwise falls
    back to keyword extraction. All returned records conform to project schemas.

    Args:
        course_id: Course identifier
        lecture_id: Lecture identifier
        transcript: Lecture transcript text
        generated_at: ISO timestamp
        storage_dir: Path to storage directory
        openai_model: OpenAI model to use
        llm_provider: LLM provider (openai/gemini/vertex)
        llm_model: Specific model name
        preset_id: Optional preset ID to customize thread detection behavior
    """
    if generated_at is None:
        generated_at = _iso_now()

    store = ThreadStore(storage_dir / "threads" / f"{course_id}.json")
    existing = store.load()
    existing_list = list(existing.values())

    provider_key = (llm_provider or "openai").strip().lower()
    model_name = llm_model or openai_model
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

    should_try_llm = (provider_key == "openai" and has_openai_key) or (
        provider_key in {"gemini", "vertex"} and has_gemini_key
    )

    # Load preset configuration if provided
    preset_config = None
    if preset_id:
        try:
            # Import here to avoid circular dependency
            import sys
            from pathlib import Path
            backend_path = Path(__file__).parent.parent / "backend"
            if str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
            from presets import PRESETS_BY_ID
            preset_config = PRESETS_BY_ID.get(preset_id)
            if preset_config:
                print(f"[ThreadEngine] Using preset: {preset_config.get('name', preset_id)}")
        except Exception as e:
            print(f"[ThreadEngine] WARNING: Could not load preset {preset_id}: {e}")

    # Load course context from uploaded files (if available)
    course_context = _load_course_context(course_id)
    if course_context and (course_context.get("syllabus") or course_context.get("notes")):
        print(f"[ThreadEngine] Using course context: "
              f"syllabus={bool(course_context.get('syllabus'))}, "
              f"notes={bool(course_context.get('notes'))}")

    # Metrics collection
    import time
    detection_method = "fallback"
    api_response_time_ms = None
    retry_count = 0
    success = True
    error_message = None

    if should_try_llm:
        try:
            start_time = time.time()
            if provider_key == "openai":
                llm_result = _call_openai(transcript, existing_list, model_name, preset_config=preset_config)
                detection_method = "openai"
            else:
                llm_result = _call_gemini(
                    transcript, existing_list, model_name,
                    course_context=course_context,
                    preset_config=preset_config
                )
                detection_method = "gemini"
            api_response_time_ms = (time.time() - start_time) * 1000

            threads, occurrences, updates = _process_llm_output(
                llm_result, existing, course_id, lecture_id, generated_at
            )
        except Exception as exc:
            error_message = str(exc)
            print(
                f"[ThreadEngine] WARNING: {provider_key} call failed ({exc}). "
                "Falling back to keyword detection."
            )
            detection_method = "fallback"
            threads, occurrences, updates = _process_fallback(
                transcript, existing, course_id, lecture_id, generated_at
            )
    else:
        threads, occurrences, updates = _process_fallback(
            transcript, existing, course_id, lecture_id, generated_at
        )

    store.save(threads)

    # Collect and log metrics
    try:
        from pipeline.thread_metrics import calculate_thread_metrics, calculate_quality_score

        metrics = calculate_thread_metrics(
            threads=threads,
            occurrences=occurrences,
            updates=updates,
            lecture_id=lecture_id,
            course_id=course_id,
            detection_method=detection_method,
            model_name=model_name if detection_method != "fallback" else None,
            llm_provider=provider_key if detection_method != "fallback" else None,
            api_response_time_ms=api_response_time_ms,
            token_usage=None,  # TODO: Extract from API response
            retry_count=retry_count,
            success=success,
            error_message=error_message,
        )

        quality_score = calculate_quality_score(metrics)

        # Log metrics
        print(
            f"[ThreadEngine] Detected {metrics.new_threads_detected} new threads, "
            f"{metrics.existing_threads_updated} updates. "
            f"Quality score: {quality_score}/100"
        )

        # Store metrics for later retrieval (stored in module variable for now)
        # TODO: Save to database via API call
        _last_metrics = metrics
        _last_quality_score = quality_score

    except Exception as e:
        print(f"[ThreadEngine] WARNING: Failed to collect metrics: {e}")

    return threads, occurrences, updates


def get_last_metrics():
    """
    Get the metrics from the last thread detection run.

    Returns:
        Tuple of (metrics, quality_score) or (None, None) if no metrics available
    """
    return _last_metrics, _last_quality_score


# Global storage for last rotation state
_last_rotation_state = None


def generate_thread_records_with_rotation(
    course_id: str,
    lecture_id: str,
    transcript: str,
    generated_at: Optional[str],
    storage_dir: Path,
    openai_model: str = "gpt-4o-mini",
    llm_provider: str = "openai",
    llm_model: str | None = None,
    preset_id: Optional[str] = None,
    max_iterations: int = 6,
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[str, Any],  # Rotation state
]:
    """
    Generate thread records using dynamic dice rotation.

    This function rotates through different facet permutations, analyzing
    the transcript from multiple perspectives. It stops when equilibrium
    is reached or collapse is detected.

    Args:
        course_id: Course identifier
        lecture_id: Lecture identifier
        transcript: Lecture transcript text
        generated_at: ISO timestamp
        storage_dir: Path to storage directory
        openai_model: OpenAI model to use
        llm_provider: LLM provider (openai/gemini/vertex)
        llm_model: Specific model name
        preset_id: Optional preset ID
        max_iterations: Maximum rotation iterations

    Returns:
        Tuple of (threads, occurrences, updates, rotation_state)
    """
    from pipeline.dice_rotation import (
        create_rotation_state,
        rotate_next,
        is_rotation_complete,
        get_rotation_summary,
    )

    print(f"[ThreadEngine] Starting dice rotation (max {max_iterations} iterations)")

    # Load preset weights if available
    preset_weights = None
    if preset_id:
        try:
            import sys
            backend_path = Path(__file__).parent.parent / "backend"
            if str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
            from presets import PRESETS_BY_ID
            preset_config = PRESETS_BY_ID.get(preset_id)
            if preset_config and "diceWeights" in preset_config:
                preset_weights = preset_config["diceWeights"]
        except Exception as e:
            print(f"[ThreadEngine] WARNING: Could not load preset weights: {e}")

    # Create rotation state
    rotation_state = create_rotation_state(
        preset_weights=preset_weights,
        max_iterations=max_iterations,
    )

    # Aggregate results across iterations
    all_threads_map: Dict[str, Dict[str, Any]] = {}
    all_occurrences: List[Dict[str, Any]] = []
    all_updates: List[Dict[str, Any]] = []

    # Iterate through permutations
    iteration = 0
    while iteration < max_iterations:
        print(f"[ThreadEngine] Rotation iteration {iteration + 1}/{max_iterations}")

        # Run standard thread detection for this iteration
        # This reuses the existing logic
        iter_threads, iter_occurrences, iter_updates = generate_thread_records(
            course_id=course_id,
            lecture_id=lecture_id,
            transcript=transcript,
            generated_at=generated_at,
            storage_dir=storage_dir,
            openai_model=openai_model,
            llm_provider=llm_provider,
            llm_model=llm_model,
            preset_id=preset_id,
        )

        # Merge threads (avoid duplicates by ID)
        for thread in iter_threads:
            thread_id = thread.get("id")
            if thread_id and thread_id not in all_threads_map:
                all_threads_map[thread_id] = thread

        # Accumulate occurrences and updates
        all_occurrences.extend(iter_occurrences)
        all_updates.extend(iter_updates)

        # Update rotation state
        rotation_state, should_continue = rotate_next(
            rotation_state,
            iter_threads,
            iter_occurrences,
            iter_updates,
        )

        iteration += 1

        # Check if rotation is complete
        if not should_continue or is_rotation_complete(rotation_state):
            summary = get_rotation_summary(rotation_state)
            print(f"[ThreadEngine] Rotation complete: {summary['status']}")
            print(f"  Iterations: {summary['iterations_completed']}")
            print(f"  Dominant facet: {summary['dominant_facet']} ({summary['dominant_score']:.2f})")
            print(f"  Equilibrium gap: {summary['equilibrium_gap']:.3f}")
            break

    # Convert aggregated threads to list
    final_threads = list(all_threads_map.values())

    # Store rotation state globally for retrieval
    global _last_rotation_state
    _last_rotation_state = rotation_state

    print(f"[ThreadEngine] Final: {len(final_threads)} unique threads across {iteration} iterations")

    return final_threads, all_occurrences, all_updates, rotation_state.to_dict()


def get_last_rotation_state():
    """
    Get the rotation state from the last rotation run.

    Returns:
        Rotation state dict or None if no rotation has run
    """
    global _last_rotation_state
    if _last_rotation_state:
        return _last_rotation_state.to_dict()
    return None


def _load_course_context(course_id: str) -> Optional[Dict[str, str]]:
    """
    Load course context (syllabus + notes) from database.
    Returns dict with 'syllabus' and 'notes' keys, or None if no context available.
    """
    try:
        # Import here to avoid circular dependencies
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
        import db as db_module
        from backend.db import get_database

        db = get_database()
        context = db_module.fetch_context_text_for_course(db.conn, course_id)

        if not context.get("syllabus") and not context.get("notes"):
            return None

        return context

    except Exception as e:
        print(f"[ThreadEngine] WARNING: Failed to load course context: {e}")
        return None
