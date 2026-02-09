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


def _get_context_descriptors(transcript: str, term: str) -> List[str]:
    """Extracts adjectives and nouns near a term to define its current 'depth'."""
    # Simple regex to find words immediately preceding the term (potential descriptors)
    pattern = rf"(\w+)\s+{re.escape(term)}"
    matches = re.findall(pattern, transcript.lower())
    return [m for m in matches if m not in STOPWORDS]

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
        matching = next((thread for thread in threads if thread["title"] == term), None)
        evidence = _sentence_for_term(transcript, term)
        descriptors = _get_context_descriptors(transcript, term)
        
        if matching is None:
            # New Thread: Initial Introduction
            thread_id = str(uuid.uuid4())
            thread = {
                "id": thread_id,
                "courseId": course_id,
                "title": term,
                "summary": f"Initial concept of '{term}' introduced.",
                "status": "foundational",
                "complexityLevel": 1,
                "lectureRefs": [lecture_id],
                "descriptors": descriptors,
                "evolutionNotes": [{
                    "lectureId": lecture_id,
                    "changeType": "refinement",
                    "note": f"Concept first introduced with terms: {', '.join(descriptors) if descriptors else 'None'}."
                }]
            }
            threads.append(thread)
        else:
            # Existing Thread: Detect Refinement or Complexity
            thread_id = matching["id"]
            prev_descriptors = set(matching.get("descriptors", []))
            new_descriptors = set(descriptors)
            
            # Refinement Logic: If we see new descriptors not present before
            added_depth = new_descriptors - prev_descriptors
            change_summary = f"Refined '{term}' with new context."
            change_type = "refinement"
            
            if len(added_depth) > 2:
                # Complexity Logic: If significant new terminology is added
                matching["complexityLevel"] = min(5, matching.get("complexityLevel", 1) + 1)
                matching["status"] = "advanced" if matching["complexityLevel"] > 2 else "foundational"
                change_type = "complexity"
                change_summary = f"Increased complexity of '{term}' via detailed descriptors: {', '.join(added_depth)}."

            # Update existing thread metadata
            matching["lectureRefs"] = sorted(list(set(matching.get("lectureRefs", []) + [lecture_id])))
            matching["descriptors"] = list(prev_descriptors | new_descriptors)
            matching.setdefault("evolutionNotes", []).append({
                "lectureId": lecture_id,
                "changeType": change_type,
                "note": change_summary
            })

            updates.append({
                "id": str(uuid.uuid4()),
                "threadId": thread_id,
                "courseId": course_id,
                "lectureId": lecture_id,
                "changeType": change_type,
                "summary": change_summary,
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

    store.save(threads)
    return threads, occurrences, updates
        )

    return threads, occurrences, updates
