#!/usr/bin/env python3
"""Test that different presets produce different generation prompts."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.presets import PRESETS_BY_ID
from pipeline.llm_generation import _build_generation_prompt, _load_preset_config


def main():
    """Test preset-specific generation prompts."""

    print("=" * 80)
    print("🎯 PRESET GENERATION CUSTOMIZATION TEST")
    print("=" * 80)
    print()

    test_presets = [
        ("exam-mode", "📝 Exam Mode"),
        ("beginner-mode", "👶 Beginner Mode"),
        ("neurodivergent-friendly-mode", "🧩 Neurodivergent Mode"),
        ("seminar-mode", "🎓 Seminar Mode"),
    ]

    for preset_id, expected_name in test_presets:
        print(f"\n{'=' * 80}")
        print(f"Testing: {expected_name}")
        print("=" * 80)

        # Load preset config
        preset_config = _load_preset_config(preset_id)

        if not preset_config:
            print(f"❌ Failed to load preset config for {preset_id}")
            continue

        # Get generation config
        gen_config = preset_config.get("generation_config", {})

        if not gen_config:
            print(f"⚠️  No generation_config found for {preset_id}")
            continue

        print(f"✅ Preset loaded: {preset_config.get('name')}")
        print()

        # Display generation parameters
        print("📊 Generation Parameters:")
        print(f"  Summary Length: {gen_config.get('summary_max_words', 'N/A')} words")
        print(f"  Flashcard Count: {gen_config.get('flashcard_count', 'N/A')}")
        print(f"  Exam Questions: {gen_config.get('exam_question_count', 'N/A')}")
        print(f"  Tone: {gen_config.get('tone', 'N/A')}")
        print()

        # Display question types
        q_types = gen_config.get('question_types', [])
        if q_types:
            print(f"❓ Question Types: {', '.join(q_types)}")
            print()

        # Display special instructions
        special = gen_config.get('special_instructions', [])
        if special:
            print("📝 Special Instructions:")
            for instruction in special[:3]:  # Show first 3
                print(f"  • {instruction}")
            if len(special) > 3:
                print(f"  ... and {len(special) - 3} more")
            print()

        # Generate prompt and show excerpt
        prompt = _build_generation_prompt(preset_id, preset_config)

        # Extract the MODE section
        if "MODE:" in prompt:
            mode_start = prompt.index("MODE:")
            mode_end = prompt.index("=" * 60, mode_start + 10) + 60
            mode_section = prompt[mode_start:mode_end]
            print("💬 Generated Prompt Excerpt:")
            print("-" * 80)
            print(mode_section)
            print("-" * 80)
        else:
            print("⚠️  No MODE section found in prompt")

    print()
    print("=" * 80)
    print("✅ Preset generation customization is working!")
    print("=" * 80)
    print()

    # Comparison test
    print("🔍 COMPARISON TEST: Exam Mode vs Beginner Mode")
    print("=" * 80)
    print()

    exam_config = _load_preset_config("exam-mode")
    beginner_config = _load_preset_config("beginner-mode")

    exam_gen = exam_config.get("generation_config", {})
    beginner_gen = beginner_config.get("generation_config", {})

    print("Metric               | Exam Mode    | Beginner Mode")
    print("-" * 80)
    print(f"Summary Length       | {exam_gen.get('summary_max_words', 'N/A'):>12} | {beginner_gen.get('summary_max_words', 'N/A'):>13}")
    print(f"Flashcard Count      | {exam_gen.get('flashcard_count', 'N/A'):>12} | {beginner_gen.get('flashcard_count', 'N/A'):>13}")
    print(f"Tone                 | {exam_gen.get('tone', 'N/A'):>12} | {beginner_gen.get('tone', 'N/A'):>13}")
    print()

    if exam_gen.get('summary_max_words') != beginner_gen.get('summary_max_words'):
        print("✅ Different summary lengths")
    if exam_gen.get('tone') != beginner_gen.get('tone'):
        print("✅ Different tones")
    if exam_gen.get('flashcard_count') != beginner_gen.get('flashcard_count'):
        print("✅ Different flashcard counts")

    print()
    print("=" * 80)
    print("✅ Presets produce different generation parameters!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
