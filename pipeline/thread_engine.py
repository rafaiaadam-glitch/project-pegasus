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
import urllib.request
import urllib.error


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
VALID_FACES = {"RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "PURPLE"}

# Module-level storage for last detection metrics
_last_metrics = None
_last_quality_score = None
_last_artifacts = None


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

def _build_system_prompt(
    preset_config: Optional[Dict[str, Any]] = None,
    generate_artifacts: bool = False,
    preset_id: str = "",
    focus_face: Optional[str] = None,
) -> str:
    """
    Build a system prompt for thread detection and optionally artifact generation.

    Args:
        preset_config: Optional preset configuration with diceWeights and emphasis
        generate_artifacts: If True, also ask the LLM to generate study artifacts
        preset_id: Preset ID for artifact customisation
        focus_face: Optional dice face (e.g. "BLUE") to prioritize in detection

    Returns:
        System prompt string
    """
    base_prompt = """\
You are the Thread Engine for Pegasus Lecture Copilot.

Your job is to analyse a university lecture transcript and extract precise,
exam-worthy keywords and key terms that a student would need to know.

DICE FACE TAGGING — every keyword must be tagged with exactly one face:
  RED    = How (methods, processes, techniques, algorithms, procedures)
  ORANGE = What (specific terms, named concepts, definitions, formulas)
  YELLOW = When (dates, eras, periods, temporal sequences, milestones)
  GREEN  = Where (places, institutions, labs, countries, regions)
  BLUE   = Who (named people, research groups, schools of thought)
  PURPLE = Why (causal explanations, motivations, design rationales)

GRANULARITY — pick the most specific term the transcript supports:
  GOOD: "Gradient Descent", "Backpropagation", "ReLU Activation"
  BAD:  "Common Algorithms", "Learning Methods", "Key Concepts"
  GOOD: "Noam Chomsky", "MIT Linguistics Lab", "1957"
  BAD:  "Famous Linguists", "Research Institutions", "Historical Context"
  GOOD: "Cross-Entropy Loss", "Bayes' Theorem", "P-value"
  BAD:  "Math Formulas", "Statistical Methods", "Loss Functions"

If the transcript mentions "supervised learning includes decision trees,
SVMs, and random forests", extract "Decision Tree", "SVM", "Random Forest"
as separate ORANGE keywords — not one umbrella "Supervised Learning" thread.

You will be given:
1. COURSE CONTEXT (if available): syllabus and notes uploaded by the student
   - Use this to understand the course structure and expected topics
   - Prioritize keywords that align with the syllabus
   - Use terminology consistent with course materials
2. The lecture transcript.
3. A list of keywords (threads) already tracked for this course."""

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

    # Inject focus-face directive for rotation
    if focus_face:
        face_to_dimension = {
            "RED": ("HOW", "methods, mechanisms, processes, and procedures"),
            "ORANGE": ("WHAT", "core concepts, definitions, and entities"),
            "YELLOW": ("WHEN", "temporal context, timelines, and sequences"),
            "GREEN": ("WHERE", "spatial, institutional, and environmental context"),
            "BLUE": ("WHO", "actors, agents, authors, and stakeholders"),
            "PURPLE": ("WHY", "rationale, purpose, causation, and motivation"),
        }
        dim = face_to_dimension.get(focus_face)
        if dim:
            base_prompt += (
                f"\n\nFOCUS: For this pass, prioritise the {dim[0]} dimension — "
                f"look especially for {dim[1]}. "
                f"Still extract concepts from other dimensions, but weight your "
                f"attention toward {dim[0]} when deciding what qualifies as a "
                f"new concept or update."
            )

    base_prompt += """

Return STRICT JSON only — no markdown, no explanation.

Return an object with two keys:

"new_concepts": array of objects (target 8–20 per lecture), one per brand-new
keyword not in the existing threads list. Each object:
  {
    "title": "<specific term, title-cased, 1–4 words>",
    "face": "<RED|ORANGE|YELLOW|GREEN|BLUE|PURPLE>",
    "summary": "<one sentence: what this term means in the lecture's context>",
    "evidence": "<verbatim quote from the transcript that mentions this term, max 160 chars>",
    "complexity_level": <integer 1–5, 1=introductory>,
    "status": "<foundational|advanced>"
  }

"concept_updates": array of objects, one per existing keyword that reappears in
this lecture with new information. Each object:
  {
    "title": "<must exactly match a title from existing_threads>",
    "change_type": "<refinement|contradiction|complexity>",
    "summary": "<one sentence describing what new information appeared>",
    "evidence": "<verbatim quote from the transcript, max 160 chars>",
    "new_complexity_level": <integer 1–5, or null if unchanged>
  }

Rules:
- ONLY extract keywords that are explicitly mentioned in the transcript.
- Evidence MUST be a direct quote — not a paraphrase. Copy the words from the transcript.
- Target 8–20 new keywords per lecture. Fewer is fine if the lecture is short or narrow.
- Each keyword MUST have a "face" field: RED, ORANGE, YELLOW, GREEN, BLUE, or PURPLE.
- REJECT vague umbrella terms. If the transcript says "methods include X, Y, Z",
  extract X, Y, Z separately — not "Methods" or "Common Techniques".
- A keyword title must be a noun phrase a student could look up or put on a flashcard.
- "contradiction" = the lecture conflicts with a previous summary for that thread.
- "complexity" = significantly deeper treatment (raise new_complexity_level).
- "refinement" = revisited with more detail or nuance.
- Return empty arrays if nothing qualifies — do not pad with filler.
- Do NOT hallucinate terms or quotes not present in the transcript.
- Each existing thread includes which lectures it appeared in. When new content
  relates to a previously covered concept, update it rather than creating a
  duplicate. Note connections to earlier lectures in your updates.
"""

    if generate_artifacts:
        artifact_instructions = """

ADDITIONALLY, generate structured study artifacts from the transcript.
Include an "artifacts" key in your response with the following sub-keys:

"artifacts": {
  "summary": {
    "overview": "<2-3 sentence overview of the lecture>",
    "sections": [
      {"title": "<section heading>", "bullets": ["<key point 1>", "<key point 2>"]}
    ]
  },
  "outline": [
    {"title": "<top-level heading>", "points": ["<sub-point>"], "children": [{"title": "...", "points": ["..."]}]}
  ],
  "key_terms": [
    {"term": "<term>", "definition": "<clear definition>"}
  ],
  "flashcards": [
    {"front": "<question or prompt>", "back": "<answer>"}
  ],
  "exam_questions": [
    {
      "prompt": "<question text>",
      "type": "multiple-choice|short-answer|true-false|essay",
      "answer": "<correct answer>",
      "choices": ["<option A>", "<option B>", "<option C>", "<option D>"] or null,
      "correctChoiceIndex": 0,
      "explanation": "<1-2 sentence explanation of why the correct answer is right>"
    }
  ]
}

Artifact rules:
- Summary must have at least 1 section with at least 1 bullet each.
- Generate 8-15 flashcards covering the main concepts.
- Generate 5-10 exam questions mixing multiple-choice, short-answer, and true-false.
- Each exam question MUST include an "explanation" field with a 1-2 sentence explanation of why the correct answer is right.
- Generate 8-15 key terms with clear definitions.
- Outline should be hierarchical, reflecting the lecture structure.
- All content must come directly from the transcript — do NOT hallucinate.
"""
        # Add preset-specific artifact instructions
        if preset_config:
            gen_config = preset_config.get("generation_config", {})
            if gen_config:
                if gen_config.get("tone"):
                    artifact_instructions += f"\nArtifact tone: {gen_config['tone']}"
                if gen_config.get("flashcard_count"):
                    artifact_instructions += f"\nTarget flashcard count: {gen_config['flashcard_count']}"
                if gen_config.get("exam_question_count"):
                    artifact_instructions += f"\nTarget exam question count: {gen_config['exam_question_count']}"
                special = gen_config.get("special_instructions", [])
                if special:
                    artifact_instructions += "\nSpecial instructions:\n" + "\n".join(f"- {s}" for s in special)

        base_prompt += artifact_instructions

    return base_prompt


_SYSTEM_PROMPT = _build_system_prompt()  # Default prompt for backward compatibility


def _call_openai(
    transcript: str,
    existing_threads: List[Dict[str, Any]],
    model: str,
    timeout: int = 300,
    course_context: Optional[Dict[str, str]] = None,
    preset_config: Optional[Dict[str, Any]] = None,
    generate_artifacts: bool = False,
    preset_id: str = "",
    focus_face: Optional[str] = None,
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
        {
            "title": t["title"],
            "summary": t["summary"],
            "lectures": t.get("lectureRefs", t.get("lecture_refs", [])),
        }
        for t in existing_threads
    ]

    # Build user content with course context
    content_parts = []
    if course_context:
        if course_context.get("syllabus"):
            content_parts.append(f"=== COURSE SYLLABUS ===\n{course_context['syllabus']}\n")
        if course_context.get("notes"):
            notes = course_context["notes"][:5000]
            content_parts.append(f"=== COURSE NOTES ===\n{notes}\n")

    content_parts.append(f"existing_threads: {json.dumps(existing_summary)}")
    content_parts.append(f"transcript:\n{transcript}")
    user_content = "\n".join(content_parts)

    # Build preset-aware system prompt with artifact generation support
    system_prompt = _build_system_prompt(
        preset_config,
        generate_artifacts=generate_artifacts,
        preset_id=preset_id,
        focus_face=focus_face,
    )

    print(f"[ThreadEngine] Calling OpenAI model={model} artifacts={generate_artifacts}")

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "text": {"format": {"type": "json_object"}},
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

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.getcode()
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="replace")[:500]
            raise NonRetryableError(
                f"OpenAI API returned HTTP {http_err.code}: {error_body}"
            ) from http_err
        except urllib.error.URLError as url_err:
            raise NonRetryableError(
                f"OpenAI API connection failed: {url_err.reason}"
            ) from url_err

        if status != 200:
            raise NonRetryableError(f"OpenAI API returned unexpected status {status}")

        try:
            raw = json.loads(body)
        except json.JSONDecodeError as je:
            raise NonRetryableError(
                f"OpenAI returned invalid JSON: {body[:200]}"
            ) from je

        # Extract text from OpenAI responses API format
        for output in raw.get("output", []):
            for content in output.get("content", []):
                if "text" in content:
                    try:
                        return json.loads(content["text"])
                    except json.JSONDecodeError as je:
                        raise NonRetryableError(
                            f"OpenAI returned non-JSON text: {content['text'][:200]}"
                        ) from je

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
    timeout: int = 300,
    course_context: Optional[Dict[str, str]] = None,
    preset_config: Optional[Dict[str, Any]] = None,
    generate_artifacts: bool = False,
    preset_id: str = "",
    focus_face: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Gemini via Vertex AI with retry logic and return parsed JSON response."""
    from google import genai
    from google.genai import types
    from pipeline.retry_utils import (
        with_retry,
        retry_config_from_env,
        NonRetryableError,
    )

    existing_summary = [
        {
            "title": t["title"],
            "summary": t["summary"],
            "lectures": t.get("lectureRefs", t.get("lecture_refs", [])),
        }
        for t in existing_threads
    ]

    # Build user content with course context
    content_parts = []
    if course_context:
        if course_context.get("syllabus"):
            content_parts.append(f"=== COURSE SYLLABUS ===\n{course_context['syllabus']}\n")
        if course_context.get("notes"):
            notes = course_context["notes"][:5000]
            content_parts.append(f"=== COURSE NOTES ===\n{notes}\n")

    content_parts.append(f"existing_threads: {json.dumps(existing_summary)}")
    content_parts.append(f"transcript:\n{transcript}")
    user_content = "\n".join(content_parts)

    # Build preset-aware system prompt with artifact generation support
    system_prompt = _build_system_prompt(
        preset_config,
        generate_artifacts=generate_artifacts,
        preset_id=preset_id,
        focus_face=focus_face,
    )

    print(f"[ThreadEngine] Calling Gemini model={model} artifacts={generate_artifacts}")

    client = genai.Client(
        vertexai=True,
        project=os.getenv("GOOGLE_CLOUD_PROJECT", "delta-student-486911-n5"),
        location=os.getenv("PLC_GENAI_REGION", "us-central1"),
    )

    def make_request() -> Dict[str, Any]:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            )

            response = client.models.generate_content(
                model=model,
                contents=[types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_content)],
                )],
                config=config,
            )

            response_text = response.text or ""
            if not response_text.strip():
                raise NonRetryableError("Gemini returned empty response")

            try:
                return json.loads(response_text)
            except json.JSONDecodeError as je:
                raise NonRetryableError(
                    f"Gemini returned non-JSON text: {response_text[:200]}"
                ) from je

        except NonRetryableError:
            raise
        except Exception as e:
            error_str = str(e)
            # Treat rate-limit / server errors as retryable by re-raising raw
            if any(code in error_str for code in ("429", "500", "503", "RESOURCE_EXHAUSTED")):
                raise
            raise NonRetryableError(f"Gemini API error: {error_str}") from e

    config = retry_config_from_env()

    try:
        return with_retry(make_request, config=config,
                         operation_name="Gemini thread detection")
    except NonRetryableError as e:
        raise RuntimeError(f"Gemini thread detection failed: {e}") from e


def get_last_artifacts() -> Optional[Dict[str, Dict[str, Any]]]:
    """Get the artifacts from the last thread detection run."""
    return _last_artifacts


def _safe_change_type(value: Any) -> str:
    if isinstance(value, str) and value in VALID_CHANGE_TYPES:
        return value
    return "refinement"


def _safe_status(value: Any) -> str:
    if isinstance(value, str) and value in VALID_STATUSES:
        return value
    return "foundational"


def _safe_face(value: Any) -> str:
    if isinstance(value, str) and value.upper() in VALID_FACES:
        return value.upper()
    return "ORANGE"  # Default to ORANGE (What) for untagged concepts


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

    # Build case-insensitive title index for deduplication
    existing_by_title: Dict[str, Dict[str, Any]] = {
        t["title"].lower(): t for t in threads
    }

    # --- New concepts (with dedup against existing titles) ---
    for concept in llm_result.get("new_concepts", []):
        if not isinstance(concept, dict):
            continue
        title = str(concept.get("title", "")).strip()
        summary = str(concept.get("summary", "")).strip()
        evidence = str(concept.get("evidence", "")).strip()
        if not title or not summary:
            continue

        complexity = _clamp_complexity(concept.get("complexity_level"), 1)
        status = _safe_status(concept.get("status"))
        face = _safe_face(concept.get("face"))

        # Dedup: if a thread with the same title already exists, merge
        matching = existing_by_title.get(title.lower())
        if matching is not None:
            thread_id = matching["id"]
            matching["summary"] = summary
            if complexity > matching.get("complexityLevel", 1):
                matching["complexityLevel"] = complexity
            if complexity > 2:
                matching["status"] = "advanced"
            refs = matching.get("lectureRefs", [])
            if lecture_id not in refs:
                matching["lectureRefs"] = sorted(set(refs + [lecture_id]))
            matching.setdefault("evolutionNotes", []).append({
                "lectureId": lecture_id,
                "changeType": "refinement",
                "note": f"Concept re-detected in lecture {lecture_id}.",
            })
            occurrences.append({
                "id": str(uuid.uuid4()),
                "threadId": thread_id,
                "courseId": course_id,
                "lectureId": lecture_id,
                "artifactId": "summary",
                "evidence": evidence[:180] or summary[:180],
                "confidence": 0.90,
                "capturedAt": generated_at,
            })
            continue

        # Genuinely new concept
        thread_id = str(uuid.uuid4())

        thread: Dict[str, Any] = {
            "id": thread_id,
            "courseId": course_id,
            "title": title,
            "summary": summary,
            "status": status,
            "complexityLevel": complexity,
            "face": face,
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
        existing_by_title[title.lower()] = thread

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

    for update in llm_result.get("concept_updates", []):
        if not isinstance(update, dict):
            continue
        title = str(update.get("title", "")).strip()
        change_type = _safe_change_type(update.get("change_type"))
        summary_text = str(update.get("summary", "")).strip()
        evidence = str(update.get("evidence", "")).strip()

        if not title or not summary_text:
            continue

        matching = existing_by_title.get(title.lower())
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
                "face": "ORANGE",
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
    generate_artifacts: bool = False,
    focus_face: Optional[str] = None,
    existing_threads: Optional[List[Dict[str, Any]]] = None,
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
        llm_provider: LLM provider (openai)
        llm_model: Specific model name
        preset_id: Optional preset ID to customize thread detection behavior
        focus_face: Optional dice face to prioritize (e.g. "BLUE")
        existing_threads: Optional list of existing thread dicts from database.
            If provided, used instead of local ThreadStore for cross-lecture
            continuity. Each dict should have id, title, summary, lecture_refs.
    """
    if generated_at is None:
        generated_at = _iso_now()

    if existing_threads is not None:
        # Use database-provided threads for cross-lecture continuity
        existing = {t["id"]: t for t in existing_threads if isinstance(t, dict) and "id" in t}
        existing_list = list(existing.values())
        print(f"[ThreadEngine] Using {len(existing_list)} existing threads from database")
    else:
        # Fallback to local ThreadStore (for CLI / local dev)
        store = ThreadStore(storage_dir / "threads" / f"{course_id}.json")
        existing = store.load()
        existing_list = list(existing.values())

    global _last_artifacts
    _last_artifacts = None

    provider_key = (llm_provider or "openai").strip().lower()
    model_name = llm_model or openai_model
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
    has_gemini_access = True  # Vertex AI uses ADC, no explicit key needed on Cloud Run

    should_try_llm = (
        (provider_key == "openai" and has_openai_key)
        or (provider_key in ("gemini", "google") and has_gemini_access)
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
            llm_call_kwargs = dict(
                transcript=transcript,
                existing_threads=existing_list,
                model=model_name,
                course_context=course_context,
                preset_config=preset_config,
                generate_artifacts=generate_artifacts,
                preset_id=preset_id or "",
                focus_face=focus_face,
            )
            if provider_key in ("gemini", "google"):
                llm_result = _call_gemini(**llm_call_kwargs)
                detection_method = "gemini"
            else:
                llm_result = _call_openai(**llm_call_kwargs)
                detection_method = "openai"
            api_response_time_ms = (time.time() - start_time) * 1000

            threads, occurrences, updates = _process_llm_output(
                llm_result, existing, course_id, lecture_id, generated_at
            )

            # Extract artifacts if present in LLM response
            if generate_artifacts and "artifacts" in llm_result:
                _last_artifacts = llm_result["artifacts"]
                print(f"[ThreadEngine] Extracted artifacts: {list(_last_artifacts.keys())}")
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

    # Persist threads locally only when using ThreadStore (not DB-provided threads)
    if existing_threads is None:
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
    existing_threads: Optional[List[Dict[str, Any]]] = None,
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
        llm_provider: LLM provider (openai)
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
        # Read the primary face from the current schedule position
        current_face = rotation_state.schedule[rotation_state.active_index][0]
        print(f"[ThreadEngine] Rotation iteration {iteration + 1}/{max_iterations} "
              f"(focus_face={current_face})")

        # Run thread detection with the focus face for this iteration
        # Generate artifacts on the first iteration so they're available to the pipeline
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
            focus_face=current_face,
            generate_artifacts=(iteration == 0),
            existing_threads=existing_threads,
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
        with db.connect() as conn:
            context = db_module.fetch_context_text_for_course(conn, course_id)

        if not context.get("syllabus") and not context.get("notes"):
            return None

        return context

    except Exception as e:
        print(f"[ThreadEngine] WARNING: Failed to load course context: {e}")
        return None
