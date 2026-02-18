"""
Thread Engine Metrics Collection

Tracks quality and performance metrics for thread detection to help
monitor and optimize the thread engine.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import json


@dataclass
class ThreadDetectionMetrics:
    """Metrics for a single thread detection run."""

    # Identifiers
    lecture_id: str
    course_id: str
    timestamp: str

    # Thread counts
    new_threads_detected: int
    existing_threads_updated: int
    total_threads_after: int

    # Quality metrics
    avg_complexity_level: float
    complexity_distribution: Dict[int, int]  # level -> count
    change_type_distribution: Dict[str, int]  # type -> count

    # Evidence quality
    avg_evidence_length: float
    threads_with_evidence: int

    # Performance metrics
    detection_method: str  # "gemini", "openai", "fallback"
    api_response_time_ms: Optional[float]
    token_usage: Optional[Dict[str, int]]  # input/output tokens
    retry_count: int

    # Model info
    model_name: Optional[str]
    llm_provider: Optional[str]

    # Status
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def calculate_thread_metrics(
    threads: List[Dict[str, Any]],
    occurrences: List[Dict[str, Any]],
    updates: List[Dict[str, Any]],
    lecture_id: str,
    course_id: str,
    detection_method: str,
    model_name: Optional[str] = None,
    llm_provider: Optional[str] = None,
    api_response_time_ms: Optional[float] = None,
    token_usage: Optional[Dict[str, int]] = None,
    retry_count: int = 0,
    success: bool = True,
    error_message: Optional[str] = None,
) -> ThreadDetectionMetrics:
    """
    Calculate comprehensive metrics from thread detection results.

    Args:
        threads: List of newly detected threads
        occurrences: List of thread occurrences in this lecture
        updates: List of updates to existing threads
        lecture_id: ID of the lecture
        course_id: ID of the course
        detection_method: Method used (gemini/openai/fallback)
        model_name: LLM model name if applicable
        llm_provider: LLM provider if applicable
        api_response_time_ms: API response time in milliseconds
        token_usage: Dict with 'input' and 'output' token counts
        retry_count: Number of retries before success
        success: Whether detection succeeded
        error_message: Error message if failed

    Returns:
        ThreadDetectionMetrics object
    """
    # Count threads
    new_threads = len(threads)
    updated_threads = len(updates)
    total_threads = len(occurrences)

    # Calculate complexity distribution
    complexity_dist: Dict[int, int] = {}
    total_complexity = 0
    thread_count_for_avg = 0

    for thread in threads:
        level = thread.get("complexityLevel", 1)
        complexity_dist[level] = complexity_dist.get(level, 0) + 1
        total_complexity += level
        thread_count_for_avg += 1

    avg_complexity = (
        total_complexity / thread_count_for_avg
        if thread_count_for_avg > 0
        else 0.0
    )

    # Calculate change type distribution
    change_type_dist: Dict[str, int] = {}
    for update in updates:
        change_type = update.get("changeType", "refinement")
        change_type_dist[change_type] = change_type_dist.get(change_type, 0) + 1

    # Calculate evidence quality
    total_evidence_length = 0
    threads_with_evidence_count = 0

    for thread in threads:
        evidence = thread.get("evidence", "")
        if evidence:
            threads_with_evidence_count += 1
            total_evidence_length += len(evidence)

    for update in updates:
        evidence = update.get("evidence", "")
        if evidence:
            threads_with_evidence_count += 1
            total_evidence_length += len(evidence)

    total_items = len(threads) + len(updates)
    avg_evidence_length = (
        total_evidence_length / threads_with_evidence_count
        if threads_with_evidence_count > 0
        else 0.0
    )

    return ThreadDetectionMetrics(
        lecture_id=lecture_id,
        course_id=course_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        new_threads_detected=new_threads,
        existing_threads_updated=updated_threads,
        total_threads_after=total_threads,
        avg_complexity_level=round(avg_complexity, 2),
        complexity_distribution=complexity_dist,
        change_type_distribution=change_type_dist,
        avg_evidence_length=round(avg_evidence_length, 1),
        threads_with_evidence=threads_with_evidence_count,
        detection_method=detection_method,
        api_response_time_ms=api_response_time_ms,
        token_usage=token_usage,
        retry_count=retry_count,
        model_name=model_name,
        llm_provider=llm_provider,
        success=success,
        error_message=error_message,
    )


def calculate_quality_score(metrics: ThreadDetectionMetrics) -> float:
    """
    Calculate a quality score (0-100) for thread detection.

    Factors:
    - Number of threads detected (more is generally better)
    - Evidence quality (longer, more detailed evidence)
    - Use of LLM vs fallback (LLM preferred)
    - Success rate (no errors)
    - Complexity distribution (balanced is good)

    Returns:
        Quality score from 0-100
    """
    score = 0.0

    # Base score for detecting threads (0-30 points)
    total_threads = metrics.new_threads_detected + metrics.existing_threads_updated
    if total_threads > 0:
        # 10 points for detecting something
        score += 10
        # Up to 20 more points based on count (diminishing returns)
        score += min(20, total_threads * 2)

    # Evidence quality (0-25 points)
    if metrics.threads_with_evidence > 0:
        # 10 points for having any evidence
        score += 10
        # Up to 15 more points based on evidence quality
        evidence_score = min(15, metrics.avg_evidence_length / 10)
        score += evidence_score

    # Detection method (0-20 points)
    if metrics.detection_method in ("gemini", "openai"):
        score += 20  # Full points for LLM
    elif metrics.detection_method == "fallback":
        score += 10  # Half points for fallback

    # Performance (0-15 points)
    if metrics.success:
        score += 10
        # Bonus for no retries
        if metrics.retry_count == 0:
            score += 5

    # Complexity distribution (0-10 points)
    # Balanced distribution is good (not all level 1 or all level 5)
    if metrics.complexity_distribution:
        levels_used = len(metrics.complexity_distribution)
        if levels_used >= 2:
            score += min(10, levels_used * 3)

    return round(min(100, score), 1)
