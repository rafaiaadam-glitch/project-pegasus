"""Permutation schedule generation for dice rotation."""

from __future__ import annotations
import random
from typing import List
from pipeline.dice_rotation.types import DiceFace


# All six dice faces
ALL_FACES: List[DiceFace] = ["RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "PURPLE"]


def generate_schedule(
    num_permutations: int = 6,
    preset_weights: dict | None = None,
    seed: int | None = None,
) -> List[List[DiceFace]]:
    """
    Generate a permutation schedule for dice rotation.

    Strategy:
    1. Start with base permutation (preset order if provided, else canonical)
    2. Generate subsequent permutations by rotating focus
    3. Ensure all facets get primary focus at least once
    4. Add controlled randomness for exploration

    Args:
        num_permutations: Number of permutations to generate (default: 6)
        preset_weights: Optional preset dice weights to inform initial order
        seed: Random seed for reproducibility

    Returns:
        List of permutations, each being a list of 6 DiceFaces
    """
    if seed is not None:
        random.seed(seed)

    schedule: List[List[DiceFace]] = []

    # First permutation: weighted order (if preset provided) or canonical
    if preset_weights:
        first = _weighted_permutation(preset_weights)
    else:
        first = list(ALL_FACES)  # Canonical order

    schedule.append(first)

    # Subsequent permutations: ensure each facet gets priority
    remaining_faces = set(ALL_FACES)
    remaining_faces.discard(first[0])  # First face already prioritized

    for i in range(1, num_permutations):
        if remaining_faces:
            # Pick next face to prioritize
            next_primary = random.choice(list(remaining_faces))
            remaining_faces.discard(next_primary)
        else:
            # All faces prioritized, use weighted shuffle
            next_primary = random.choice(ALL_FACES)

        # Build permutation with this face first
        perm = [next_primary]
        others = [f for f in ALL_FACES if f != next_primary]
        random.shuffle(others)
        perm.extend(others)

        schedule.append(perm)

    return schedule


def _weighted_permutation(weights: dict) -> List[DiceFace]:
    """
    Create initial permutation based on preset weights.

    Args:
        weights: Dict mapping facet names (what, how, etc.) to weights

    Returns:
        List of DiceFaces sorted by weight (descending)
    """
    from pipeline.dice_rotation.types import FACET_TO_FACE

    # Map weights to faces
    face_weights: List[tuple[DiceFace, float]] = []
    for facet, weight in weights.items():
        if facet in FACET_TO_FACE:
            face = FACET_TO_FACE[facet]
            face_weights.append((face, weight))

    # Sort by weight descending
    face_weights.sort(key=lambda x: x[1], reverse=True)

    # Extract faces
    return [face for face, _ in face_weights]


def rotate_permutation(perm: List[DiceFace], steps: int = 1) -> List[DiceFace]:
    """
    Rotate a permutation by N steps.

    Args:
        perm: Current permutation
        steps: Number of positions to rotate

    Returns:
        Rotated permutation
    """
    n = len(perm)
    steps = steps % n
    return perm[steps:] + perm[:steps]


def generate_balanced_schedule() -> List[List[DiceFace]]:
    """
    Generate a balanced schedule where each face appears in each position exactly once.

    This creates a Latin square-like structure for maximum exploration.

    Returns:
        6x6 schedule where each face appears once per position
    """
    schedule: List[List[DiceFace]] = []

    # Start with canonical order
    base = list(ALL_FACES)
    schedule.append(base)

    # Rotate to create Latin square pattern
    for i in range(1, 6):
        rotated = rotate_permutation(base, i)
        schedule.append(rotated)

    return schedule
