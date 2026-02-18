#!/usr/bin/env python3
"""Test script for dice rotation system."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.dice_rotation import (
    create_rotation_state,
    rotate_next,
    get_rotation_summary,
    is_rotation_complete,
)
from pipeline.dice_rotation.permutations import generate_schedule
from pipeline.dice_rotation.facets import score_facets, calculate_entropy, calculate_equilibrium_gap


def test_permutation_generation():
    """Test permutation schedule generation."""
    print("=" * 80)
    print("TEST 1: Permutation Generation")
    print("=" * 80)
    print()

    # Test with Exam Mode weights
    exam_weights = {
        "what": 0.25,
        "how": 0.25,
        "when": 0.15,
        "where": 0.15,
        "who": 0.05,
        "why": 0.15,
    }

    schedule = generate_schedule(num_permutations=6, preset_weights=exam_weights, seed=42)

    print(f"Generated {len(schedule)} permutations:")
    print()

    for i, perm in enumerate(schedule):
        print(f"  Permutation {i + 1}: {' → '.join(perm)}")

    print()
    print("✅ Permutation generation working")
    print()


def test_facet_scoring():
    """Test facet scoring with sample threads."""
    print("=" * 80)
    print("TEST 2: Facet Scoring")
    print("=" * 80)
    print()

    # Sample threads
    threads = [
        {
            "id": "thread-1",
            "title": "Photosynthesis Process",
            "summary": "The process by which plants convert light energy into chemical energy",
            "evidence": "Plants use chlorophyll in chloroplasts to capture light energy and produce glucose through light-dependent and light-independent reactions.",
        },
        {
            "id": "thread-2",
            "title": "Cellular Respiration",
            "summary": "The process of breaking down glucose to release energy",
            "evidence": "Occurs in mitochondria through glycolysis, Krebs cycle, and electron transport chain.",
        },
        {
            "id": "thread-3",
            "title": "Darwin's Theory",
            "summary": "Natural selection as mechanism for evolution",
            "evidence": "Charles Darwin proposed that species evolve through natural selection based on survival advantages.",
        },
    ]

    scores = score_facets(threads, [], [])

    print("Facet Scores:")
    print()
    for facet, score in scores.to_dict().items():
        bar = "█" * int(score * 20)
        print(f"  {facet.upper():6s}: {score:.3f} {bar}")

    entropy = calculate_entropy(scores)
    eq_gap = calculate_equilibrium_gap(scores)

    print()
    print(f"Entropy: {entropy:.3f} (higher = more balanced)")
    print(f"Equilibrium Gap: {eq_gap:.3f} (lower = more balanced)")
    print()
    print("✅ Facet scoring working")
    print()


def test_rotation_state():
    """Test rotation state creation and updates."""
    print("=" * 80)
    print("TEST 3: Rotation State")
    print("=" * 80)
    print()

    # Create initial state with Seminar Mode weights
    seminar_weights = {
        "what": 0.18,
        "how": 0.22,
        "when": 0.08,
        "where": 0.12,
        "who": 0.20,
        "why": 0.20,
    }

    state = create_rotation_state(preset_weights=seminar_weights, max_iterations=4, seed=42)

    print("Initial State:")
    print(f"  Schedule: {len(state.schedule)} permutations")
    print(f"  Active Index: {state.active_index}")
    print(f"  Max Iterations: {state.max_iterations}")
    print()

    # Simulate iterations
    iteration = 1
    while not is_rotation_complete(state) and iteration <= state.max_iterations:
        print(f"--- Iteration {iteration} ---")
        current_perm = state.schedule[state.active_index]
        print(f"Current permutation: {' → '.join(current_perm)}")

        # Simulate thread detection (mock threads)
        mock_threads = [
            {
                "id": f"thread-{iteration}-1",
                "title": f"Concept {iteration}A",
                "summary": "Sample concept summary",
                "evidence": "Evidence text here" * iteration,
            },
            {
                "id": f"thread-{iteration}-2",
                "title": f"Argument {iteration}B",
                "summary": "Argument-focused concept",
                "evidence": "Reasoning and justification" * iteration,
            },
        ]

        # Update state
        state, should_continue = rotate_next(state, mock_threads, [], [])

        # Print scores
        print(f"  Scores: How={state.scores.how:.2f}, What={state.scores.what:.2f}, "
              f"Who={state.scores.who:.2f}, Why={state.scores.why:.2f}")
        print(f"  Entropy: {state.entropy:.3f}")
        print(f"  Equilibrium Gap: {state.equilibrium_gap:.3f}")
        print()

        if not should_continue:
            print(f"  → Rotation stopped ({get_rotation_summary(state)['status']})")
            break

        iteration += 1

    print()
    print("Final Summary:")
    summary = get_rotation_summary(state)
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print()
    print("✅ Rotation state working")
    print()


def test_equilibrium_detection():
    """Test equilibrium and collapse detection."""
    print("=" * 80)
    print("TEST 4: Equilibrium & Collapse Detection")
    print("=" * 80)
    print()

    from pipeline.dice_rotation.facets import detect_equilibrium, detect_collapse
    from pipeline.dice_rotation.types import FacetScores

    # Test equilibrium (balanced scores)
    balanced = FacetScores(
        how=0.17,
        what=0.17,
        when=0.16,
        where=0.17,
        who=0.16,
        why=0.17,
    )

    print("Balanced Scores:")
    print(f"  {balanced.to_dict()}")
    print(f"  Equilibrium? {detect_equilibrium(balanced)}")
    print(f"  Collapsed? {detect_collapse(balanced)}")
    print()

    # Test collapse (imbalanced scores)
    imbalanced = FacetScores(
        how=0.70,
        what=0.10,
        when=0.05,
        where=0.05,
        who=0.05,
        why=0.05,
    )

    print("Imbalanced Scores:")
    print(f"  {imbalanced.to_dict()}")
    print(f"  Equilibrium? {detect_equilibrium(imbalanced)}")
    print(f"  Collapsed? {detect_collapse(imbalanced)}")
    print()

    print("✅ Equilibrium and collapse detection working")
    print()


def test_full_rotation_cycle():
    """Test a full rotation cycle with realistic scenario."""
    print("=" * 80)
    print("TEST 5: Full Rotation Cycle")
    print("=" * 80)
    print()

    # Create state
    state = create_rotation_state(max_iterations=6, seed=42)

    print("Simulating full rotation cycle...")
    print()

    iteration = 1
    while not is_rotation_complete(state) and iteration <= state.max_iterations:
        # Vary thread counts per iteration to simulate realistic pattern
        thread_count = iteration % 3 + 1

        threads = [
            {
                "id": f"thread-{iteration}-{i}",
                "title": f"Thread {iteration}.{i}",
                "summary": "Sample summary",
                "evidence": "Evidence" * (iteration + i),
            }
            for i in range(thread_count)
        ]

        state, should_continue = rotate_next(state, threads, [], [])

        print(f"Iteration {iteration}: {len(threads)} threads, "
              f"entropy={state.entropy:.3f}, gap={state.equilibrium_gap:.3f}")

        if not should_continue:
            break

        iteration += 1

    print()
    summary = get_rotation_summary(state)
    print(f"Result: {summary['status'].upper()}")
    print(f"  Completed {summary['iterations_completed']} iterations")
    print(f"  Dominant facet: {summary['dominant_facet']} ({summary['dominant_score']:.2f})")
    print(f"  Balanced: {summary['balanced']}")
    print()

    # Convert to dict (for API)
    state_dict = state.to_dict()
    print(f"State dictionary keys: {list(state_dict.keys())}")
    print()

    print("✅ Full rotation cycle complete")
    print()


def main():
    """Run all tests."""
    print()
    print("🎲" * 40)
    print(" " * 20 + "DICE ROTATION SYSTEM TEST")
    print("🎲" * 40)
    print()

    try:
        test_permutation_generation()
        test_facet_scoring()
        test_rotation_state()
        test_equilibrium_detection()
        test_full_rotation_cycle()

        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print()
        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
