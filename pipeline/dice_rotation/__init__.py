"""
Dice Rotation System for Pegasus Thread Engine.

This module implements dynamic facet rotation for balanced thread detection.
It generates permutation schedules, scores facets, and detects equilibrium/collapse states.
"""

from pipeline.dice_rotation.types import DiceFace, FacetScores, RotationState
from pipeline.dice_rotation.permutations import generate_schedule
from pipeline.dice_rotation.facets import score_facets, detect_equilibrium, detect_collapse
from pipeline.dice_rotation.rotate import (
    create_rotation_state,
    rotate_next,
    get_rotation_summary,
    is_rotation_complete,
)

__all__ = [
    "DiceFace",
    "FacetScores",
    "RotationState",
    "generate_schedule",
    "score_facets",
    "detect_equilibrium",
    "detect_collapse",
    "create_rotation_state",
    "rotate_next",
    "get_rotation_summary",
    "is_rotation_complete",
]
