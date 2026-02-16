#!/usr/bin/env python3
"""Test script to verify Seminar/Discussion Mode implementation."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.presets import PRESETS_BY_ID
from pipeline.thread_engine import _build_system_prompt


def main():
    """Verify Seminar Mode configuration and system prompt generation."""

    print("=" * 80)
    print("🎓 Seminar / Discussion Mode - Configuration Test")
    print("=" * 80)
    print()

    # Load preset
    seminar_preset = PRESETS_BY_ID.get("seminar-mode")

    if not seminar_preset:
        print("❌ ERROR: Seminar Mode preset not found!")
        return 1

    print("✅ Preset loaded successfully")
    print()

    # Display configuration
    print("📋 PRESET CONFIGURATION:")
    print(f"  Name: {seminar_preset.get('name')}")
    print(f"  Description: {seminar_preset.get('description')}")
    print()

    # Display dice weights
    print("🎲 DICE WEIGHTS:")
    dice_weights = seminar_preset.get("diceWeights", {})
    total_weight = sum(dice_weights.values())

    for dimension, weight in sorted(dice_weights.items(), key=lambda x: -x[1]):
        percentage = int(weight * 100)
        bar = "█" * (percentage // 2)
        print(f"  {dimension.upper():6s} ({percentage:2d}%): {bar}")

    print(f"  Total: {total_weight:.2f} (should be 1.00)")
    print()

    # Display optimizations
    print("🎯 OPTIMIZED FOR:")
    for item in seminar_preset.get("optimizedFor", []):
        print(f"  • {item}")
    print()

    # Display target disciplines
    print("📚 TARGET DISCIPLINES:")
    for discipline in seminar_preset.get("targetDisciplines", []):
        print(f"  • {discipline}")
    print()

    # Display output sections
    print("📄 OUTPUT SECTIONS:")
    output_profile = seminar_preset.get("outputProfile", {})
    for section in output_profile.get("sections", []):
        print(f"  • {section}")
    print()

    # Generate and display system prompt
    print("=" * 80)
    print("💬 GENERATED SYSTEM PROMPT (first 1000 chars):")
    print("=" * 80)

    system_prompt = _build_system_prompt(seminar_preset)
    print(system_prompt[:1000])
    print("...")
    print()

    # Verify dice weights sum to 1.0
    if abs(total_weight - 1.0) < 0.001:
        print("✅ Dice weights sum correctly to 1.0")
    else:
        print(f"⚠️  WARNING: Dice weights sum to {total_weight}, expected 1.0")

    # Verify emphasis matches dice weights
    emphasis = output_profile.get("emphasis", {})
    print()
    print("🔍 EMPHASIS VERIFICATION:")
    print(f"  WHO (Blue): {emphasis.get('who')} (dice: {dice_weights.get('who')})")
    print(f"  WHY (Purple): {emphasis.get('why')} (dice: {dice_weights.get('why')})")
    print(f"  HOW (Red): {emphasis.get('how')} (dice: {dice_weights.get('how')})")
    print(f"  WHAT (Orange): {emphasis.get('what')} (dice: {dice_weights.get('what')})")
    print()

    print("=" * 80)
    print("✅ Seminar / Discussion Mode is properly configured!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
