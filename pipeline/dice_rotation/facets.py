"""Facet scoring and equilibrium detection."""

from __future__ import annotations
import math
from typing import Dict, List, Any
from pipeline.dice_rotation.types import Facet, FacetScores


# Equilibrium threshold: gap below this = equilibrium
EQUILIBRIUM_THRESHOLD = 0.15

# Collapse threshold: imbalance above this = collapse
COLLAPSE_THRESHOLD = 0.65


def score_facets(
    threads: List[Dict[str, Any]],
    occurrences: List[Dict[str, Any]],
    updates: List[Dict[str, Any]],
) -> FacetScores:
    """
    Score each facet based on thread detection results.

    Scoring strategy:
    - Count threads that relate to each facet
    - Weight by evidence quality (length, specificity)
    - Normalize to [0, 1] range

    Args:
        threads: List of detected threads
        occurrences: Thread occurrences in lecture
        updates: Thread updates from this lecture

    Returns:
        FacetScores with confidence per facet
    """
    scores = FacetScores()

    if not threads and not occurrences and not updates:
        # No data, return zero scores
        return scores

    # Count contributions per facet
    facet_counts: Dict[Facet, int] = {
        "how": 0,
        "what": 0,
        "when": 0,
        "where": 0,
        "who": 0,
        "why": 0,
    }

    facet_evidence_quality: Dict[Facet, float] = {
        "how": 0.0,
        "what": 0.0,
        "when": 0.0,
        "where": 0.0,
        "who": 0.0,
        "why": 0.0,
    }

    # Analyze threads for facet alignment
    for thread in threads:
        title = thread.get("title", "").lower()
        summary = thread.get("summary", "").lower()
        evidence = thread.get("evidence", "")

        # Keyword-based facet detection
        facet = _detect_primary_facet(title, summary)
        facet_counts[facet] += 1

        # Evidence quality (longer evidence = higher confidence)
        quality = min(len(evidence) / 160.0, 1.0)  # Normalize to [0, 1]
        facet_evidence_quality[facet] += quality

    # Analyze occurrences (recurring threads indicate strong facet)
    for occurrence in occurrences:
        # Occurrences suggest facet relevance
        # We don't have direct facet info, so distribute evenly
        # In practice, this could be enhanced with NLP
        for facet in facet_counts.keys():
            facet_counts[facet] += 0.1

    # Analyze updates (evolving threads = high facet engagement)
    for update in updates:
        change_type = update.get("change_type", "refinement")

        # Different change types indicate different facet strengths
        if change_type == "complexity":
            # Complexity suggests "how" or "what" deepening
            facet_counts["how"] += 0.5
            facet_counts["what"] += 0.3
        elif change_type == "contradiction":
            # Contradiction suggests "why" or "how" evolution
            facet_counts["why"] += 0.5
            facet_counts["how"] += 0.3
        else:  # refinement
            # Refinement is neutral, slight boost to all
            for facet in facet_counts.keys():
                facet_counts[facet] += 0.1

    # Normalize counts to scores [0, 1]
    max_count = max(facet_counts.values()) if facet_counts else 1.0
    if max_count == 0:
        max_count = 1.0

    for facet in facet_counts.keys():
        raw_score = facet_counts[facet] / max_count

        # Blend with evidence quality
        quality_score = facet_evidence_quality[facet] / max(1, facet_counts[facet])
        final_score = 0.7 * raw_score + 0.3 * quality_score

        scores.set(facet, min(final_score, 1.0))

    return scores


def _detect_primary_facet(title: str, summary: str) -> Facet:
    """
    Detect primary facet from thread title and summary using keywords.

    Args:
        title: Thread title
        summary: Thread summary

    Returns:
        Primary facet (how, what, when, where, who, why)
    """
    text = f"{title} {summary}".lower()

    # Keyword patterns for each facet
    patterns = {
        "how": ["method", "process", "mechanism", "procedure", "technique", "approach", "strategy"],
        "what": ["concept", "definition", "term", "idea", "principle", "theory", "model"],
        "when": ["timeline", "period", "era", "sequence", "chronology", "temporal", "history"],
        "where": ["location", "context", "setting", "environment", "geography", "institutional"],
        "who": ["actor", "agent", "author", "speaker", "stakeholder", "person", "group"],
        "why": ["reason", "purpose", "rationale", "cause", "motivation", "justification", "goal"],
    }

    # Count keyword matches per facet
    facet_matches: Dict[Facet, int] = {facet: 0 for facet in patterns.keys()}

    for facet, keywords in patterns.items():
        for keyword in keywords:
            if keyword in text:
                facet_matches[facet] += 1

    # Return facet with most matches, default to "what" if tie
    if all(count == 0 for count in facet_matches.values()):
        return "what"

    return max(facet_matches.items(), key=lambda x: x[1])[0]


def calculate_entropy(scores: FacetScores) -> float:
    """
    Calculate Shannon entropy of facet score distribution.

    High entropy = balanced distribution
    Low entropy = concentrated on few facets

    Args:
        scores: Facet scores

    Returns:
        Entropy value (0 to ~2.58 for 6 categories)
    """
    values = [
        scores.how,
        scores.what,
        scores.when,
        scores.where,
        scores.who,
        scores.why,
    ]

    # Normalize to probability distribution
    total = sum(values)
    if total == 0:
        return 0.0

    probs = [v / total for v in values]

    # Calculate Shannon entropy: H = -Σ(p * log2(p))
    entropy = 0.0
    for p in probs:
        if p > 0:
            entropy -= p * math.log2(p)

    return entropy


def calculate_equilibrium_gap(scores: FacetScores) -> float:
    """
    Calculate gap to equilibrium (perfect balance).

    Perfect equilibrium = all facets equal = 1/6 ≈ 0.167

    Args:
        scores: Facet scores

    Returns:
        Gap value (0 = perfect equilibrium, higher = more imbalanced)
    """
    values = [
        scores.how,
        scores.what,
        scores.when,
        scores.where,
        scores.who,
        scores.why,
    ]

    # Normalize to sum = 1
    total = sum(values)
    if total == 0:
        return 1.0  # Maximum gap (no data)

    normalized = [v / total for v in values]

    # Perfect equilibrium = 1/6 for each facet
    equilibrium_value = 1.0 / 6.0

    # Calculate mean absolute deviation from equilibrium
    gap = sum(abs(v - equilibrium_value) for v in normalized) / len(normalized)

    return gap


def detect_equilibrium(scores: FacetScores, threshold: float = EQUILIBRIUM_THRESHOLD) -> bool:
    """
    Detect if system is in equilibrium (balanced state).

    Args:
        scores: Current facet scores
        threshold: Equilibrium gap threshold

    Returns:
        True if in equilibrium, False otherwise
    """
    gap = calculate_equilibrium_gap(scores)
    return gap < threshold


def detect_collapse(scores: FacetScores, threshold: float = COLLAPSE_THRESHOLD) -> bool:
    """
    Detect if system has collapsed (severe imbalance).

    Collapse occurs when one facet dominates excessively.

    Args:
        scores: Current facet scores
        threshold: Collapse threshold (fraction of total)

    Returns:
        True if collapsed, False otherwise
    """
    values = [
        scores.how,
        scores.what,
        scores.when,
        scores.where,
        scores.who,
        scores.why,
    ]

    total = sum(values)
    if total == 0:
        return False

    # Check if any single facet exceeds threshold
    normalized = [v / total for v in values]
    max_facet_proportion = max(normalized)

    return max_facet_proportion > threshold
