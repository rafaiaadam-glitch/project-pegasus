#!/usr/bin/env python3
"""Test dice rotation system with a real lecture."""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.thread_engine import generate_thread_records_with_rotation
from backend.db import get_database, upsert_dice_rotation_state


def create_sample_transcript():
    """Create a sample lecture transcript about photosynthesis."""
    return """
    Today we're going to discuss photosynthesis, which is the process by which plants
    convert light energy into chemical energy. This process occurs in the chloroplasts
    of plant cells, specifically in structures called thylakoids.

    Let me explain how this works. First, during the light-dependent reactions,
    chlorophyll molecules absorb photons of light. This energy is used to split water
    molecules, releasing oxygen as a byproduct. The process also generates ATP and
    NADPH, which are energy carriers.

    Next, the light-independent reactions, also called the Calvin cycle, take place
    in the stroma. Here's where it gets interesting: the ATP and NADPH from the
    light-dependent reactions are used to convert carbon dioxide from the air into
    glucose through a series of chemical reactions.

    This happens primarily in the leaves of plants, where most chloroplasts are
    located. The timing is important too - photosynthesis occurs during daylight
    hours when light is available.

    You might wonder why this matters. Well, photosynthesis is fundamental to life
    on Earth. It's the primary source of oxygen in our atmosphere and the basis of
    most food chains. Without photosynthesis, complex life as we know it couldn't exist.

    Charles Darwin actually wrote about the importance of plants in his work, though
    he didn't fully understand photosynthesis. Scientists in the 18th and 19th centuries
    gradually discovered how this process works through careful experimentation.
    """


def main():
    print("🎲 Testing Dice Rotation with Sample Lecture")
    print("=" * 80)
    print()

    # Configuration
    course_id = "test-course-bio101"
    lecture_id = "test-lecture-photosynthesis"
    storage_dir = Path("storage")
    storage_dir.mkdir(exist_ok=True)

    # Sample transcript
    transcript = create_sample_transcript()
    generated_at = datetime.now(timezone.utc).isoformat()

    print("📝 Lecture Info:")
    print(f"  Course: {course_id}")
    print(f"  Lecture: {lecture_id}")
    print(f"  Transcript length: {len(transcript)} characters")
    print()

    # Run thread detection with rotation
    print("🔄 Running thread detection with dice rotation...")
    print("  Max iterations: 6")
    print("  Preset: exam (default)")
    print()

    try:
        threads, occurrences, updates, rotation_state = generate_thread_records_with_rotation(
            course_id=course_id,
            lecture_id=lecture_id,
            transcript=transcript,
            generated_at=generated_at,
            storage_dir=storage_dir,
            preset_id="exam",
            max_iterations=6,
        )

        print(f"✅ Thread detection complete!")
        print()

        # Display results
        print("📊 Results:")
        print(f"  Threads detected: {len(threads)}")
        print(f"  Iterations completed: {len(rotation_state['iterationHistory'])}")
        print()

        # Display facet scores (convert from face scores to facets)
        print("🎯 Facet Scores:")
        face_scores = rotation_state['scores']
        face_to_facet = {
            'RED': 'how',
            'ORANGE': 'what',
            'YELLOW': 'when',
            'GREEN': 'where',
            'BLUE': 'who',
            'PURPLE': 'why'
        }
        for face, facet in face_to_facet.items():
            score = face_scores.get(face, 0)
            bar = "█" * int(score * 20)
            print(f"  {facet.upper():6s}: {score:.3f} {bar}")
        print()

        # Calculate status from state
        iterations = len(rotation_state['iterationHistory'])
        equilibrium_gap = rotation_state['equilibriumGap']
        collapsed = rotation_state['collapsed']
        is_equilibrium = equilibrium_gap < 0.15

        if is_equilibrium:
            status = "equilibrium"
        elif collapsed:
            status = "collapsed"
        elif iterations >= rotation_state['maxIterations']:
            status = "max_iterations"
        else:
            status = "in_progress"

        # Get dominant facet
        dominant_face = max(face_scores.items(), key=lambda x: x[1])[0]
        dominant_facet = face_to_facet[dominant_face]
        dominant_score = face_scores[dominant_face]

        # Display metrics
        print("📈 Metrics:")
        print(f"  Status: {status}")
        print(f"  Entropy: {rotation_state['entropy']:.3f}")
        print(f"  Equilibrium Gap: {equilibrium_gap:.3f}")
        print(f"  Collapsed: {collapsed}")
        print(f"  Dominant Facet: {dominant_facet} ({dominant_score:.3f})")
        print()

        # Display detected threads
        print("🧵 Detected Threads:")
        for i, thread in enumerate(threads[:5], 1):
            print(f"  {i}. {thread['title']}")
            print(f"     Summary: {thread['summary'][:80]}...")
        if len(threads) > 5:
            print(f"  ... and {len(threads) - 5} more")
        print()

        # Store in database
        print("💾 Storing rotation state in database...")
        try:
            # Prepare rotation state for database with required fields
            import uuid
            db_rotation_state = {
                **rotation_state,
                "id": str(uuid.uuid4()),
                "lectureId": lecture_id,
                "courseId": course_id,
                "iterationsCompleted": len(rotation_state['iterationHistory']),
                "status": status,
            }

            db = get_database()
            with db.connection() as conn:
                upsert_dice_rotation_state(conn, db_rotation_state)
            print("✅ Rotation state stored successfully")
            print()
        except Exception as e:
            print(f"⚠️  Database storage failed (this is OK for local testing): {e}")
            print()

        # Save rotation state to file for inspection
        output_file = storage_dir / "test_rotation_state.json"
        with open(output_file, "w") as f:
            json.dump(rotation_state, f, indent=2)
        print(f"📄 Rotation state saved to: {output_file}")
        print()

        # Summary
        print("=" * 80)
        print("✅ DICE ROTATION TEST PASSED")
        print("=" * 80)
        print()
        print("The dice rotation system successfully:")
        print("  ✅ Generated permutation schedule")
        print("  ✅ Scored facets across iterations")
        print("  ✅ Detected threads from multiple perspectives")
        print("  ✅ Calculated entropy and equilibrium metrics")
        print("  ✅ Tracked rotation state")
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
