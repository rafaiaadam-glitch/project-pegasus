"""Main rotation engine for dice system."""

from __future__ import annotations
import hmac
import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from pipeline.dice_rotation.types import (
    DiceFace,
    Facet,
    FacetScores,
    RotationState,
    IterationResult,
    FACE_TO_FACET,
)
from pipeline.dice_rotation.permutations import generate_schedule
from pipeline.dice_rotation.facets import (
    score_facets,
    calculate_entropy,
    calculate_equilibrium_gap,
    detect_equilibrium,
    detect_collapse,
)


def _compute_schedule_hmac(schedule: List[List[DiceFace]], nonce: str) -> str:
    """Compute HMAC-SHA256 of the serialized schedule, keyed by the nonce."""
    return hmac.new(
        nonce.encode(),
        json.dumps(schedule).encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_schedule_integrity(state: RotationState) -> bool:
    """
    Verify that the schedule has not been tampered with.

    Recomputes HMAC-SHA256 from state.schedule + state.nonce and
    compares against state.schedule_hmac using constant-time comparison.

    Args:
        state: RotationState with nonce and schedule_hmac fields

    Returns:
        True if schedule is intact, False if tampered or missing HMAC
    """
    if not state.nonce or not state.schedule_hmac:
        return False
    expected = _compute_schedule_hmac(state.schedule, state.nonce)
    return hmac.compare_digest(expected, state.schedule_hmac)


def create_rotation_state(
    preset_weights: dict | None = None,
    max_iterations: int = 6,
) -> RotationState:
    """
    Create initial rotation state with HMAC commitment.

    Uses cryptographically secure randomness for schedule generation
    and produces an HMAC-SHA256 commitment for tamper detection.

    Args:
        preset_weights: Optional preset dice weights
        max_iterations: Maximum number of rotation iterations

    Returns:
        Initial RotationState with nonce and schedule_hmac set
    """
    # Generate permutation schedule (CSPRNG-backed)
    schedule = generate_schedule(
        num_permutations=max_iterations,
        preset_weights=preset_weights,
    )

    # Generate HMAC commitment
    nonce = secrets.token_hex(32)
    schedule_hmac = _compute_schedule_hmac(schedule, nonce)

    # Initialize state
    state = RotationState(
        schedule=schedule,
        active_index=0,
        scores=FacetScores(),
        entropy=0.0,
        equilibrium_gap=1.0,  # Start far from equilibrium
        collapsed=False,
        iteration_history=[],
        max_iterations=max_iterations,
        nonce=nonce,
        schedule_hmac=schedule_hmac,
    )

    return state


def rotate_next(
    state: RotationState,
    threads: List[Dict[str, Any]],
    occurrences: List[Dict[str, Any]],
    updates: List[Dict[str, Any]],
) -> Tuple[RotationState, bool]:
    """
    Process next rotation iteration and update state.

    Args:
        state: Current rotation state
        threads: Threads detected in this iteration
        occurrences: Thread occurrences
        updates: Thread updates

    Returns:
        Tuple of (updated_state, should_continue)
        - updated_state: New rotation state
        - should_continue: True if rotation should continue, False if done
    """
    # Score facets from this iteration
    iteration_scores = score_facets(threads, occurrences, updates)

    # Get current permutation
    current_perm = state.schedule[state.active_index]
    primary_face = current_perm[0]
    primary_facet = FACE_TO_FACET[primary_face]

    # Record iteration result
    iteration = IterationResult(
        index=state.active_index,
        permutation=current_perm,
        primary_facet=primary_facet,
        threads_found=len(threads),
        facet_scores=iteration_scores,
        timestamp=_iso_now(),
    )

    # Update cumulative scores (weighted average with previous)
    if state.iteration_history:
        # Blend with previous scores (70% current, 30% new)
        alpha = 0.7
        state.scores.how = alpha * state.scores.how + (1 - alpha) * iteration_scores.how
        state.scores.what = alpha * state.scores.what + (1 - alpha) * iteration_scores.what
        state.scores.when = alpha * state.scores.when + (1 - alpha) * iteration_scores.when
        state.scores.where = alpha * state.scores.where + (1 - alpha) * iteration_scores.where
        state.scores.who = alpha * state.scores.who + (1 - alpha) * iteration_scores.who
        state.scores.why = alpha * state.scores.why + (1 - alpha) * iteration_scores.why
    else:
        # First iteration, use raw scores
        state.scores = iteration_scores

    # Add to history
    state.iteration_history.append(iteration)

    # Recalculate metrics
    state.entropy = calculate_entropy(state.scores)
    state.equilibrium_gap = calculate_equilibrium_gap(state.scores)

    # Check for collapse
    if detect_collapse(state.scores):
        state.collapsed = True
        return state, False  # Stop rotation

    # Check for equilibrium
    if detect_equilibrium(state.scores):
        return state, False  # Stop rotation (equilibrium reached)

    # Check max iterations
    if state.active_index >= state.max_iterations - 1:
        return state, False  # Stop rotation (max iterations)

    # Continue to next permutation
    state.active_index += 1
    return state, True


def get_current_permutation(state: RotationState) -> List[DiceFace]:
    """
    Get current active permutation.

    Args:
        state: Rotation state

    Returns:
        Current permutation (list of DiceFaces)
    """
    return state.schedule[state.active_index]


def get_primary_facet(state: RotationState) -> Facet:
    """
    Get primary facet for current rotation.

    Args:
        state: Rotation state

    Returns:
        Primary facet (first in current permutation)
    """
    current_perm = get_current_permutation(state)
    primary_face = current_perm[0]
    return FACE_TO_FACET[primary_face]


def is_rotation_complete(state: RotationState) -> bool:
    """
    Check if rotation is complete.

    Args:
        state: Rotation state

    Returns:
        True if rotation should stop, False otherwise
    """
    # Check equilibrium
    if detect_equilibrium(state.scores):
        return True

    # Check collapse
    if state.collapsed:
        return True

    # Check max iterations
    if state.active_index >= state.max_iterations - 1:
        return True

    return False


def get_rotation_summary(state: RotationState) -> Dict[str, Any]:
    """
    Get human-readable summary of rotation state.

    Args:
        state: Rotation state

    Returns:
        Summary dictionary
    """
    status = "equilibrium" if detect_equilibrium(state.scores) else \
             "collapsed" if state.collapsed else \
             "in_progress" if state.active_index < state.max_iterations - 1 else \
             "max_iterations"

    # Get dominant facet
    face_scores = state.scores.as_face_scores()
    dominant_face = max(face_scores.items(), key=lambda x: x[1])[0]
    dominant_facet = FACE_TO_FACET[dominant_face]

    return {
        "status": status,
        "iterations_completed": len(state.iteration_history),
        "dominant_facet": dominant_facet,
        "dominant_score": face_scores[dominant_face],
        "entropy": state.entropy,
        "equilibrium_gap": state.equilibrium_gap,
        "balanced": detect_equilibrium(state.scores),
        "collapsed": state.collapsed,
    }


def _iso_now() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()
