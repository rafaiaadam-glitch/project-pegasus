#!/usr/bin/env python3
"""Verify all presets have proper dice weight configuration."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.presets import PRESETS


def verify_dice_weights(preset):
    """Verify dice weights for a preset."""
    dice_weights = preset.get("diceWeights", {})

    if not dice_weights:
        return False, "No dice weights defined"

    # Check all dimensions present
    required = {"what", "how", "when", "where", "who", "why"}
    missing = required - set(dice_weights.keys())
    if missing:
        return False, f"Missing dimensions: {missing}"

    # Check sum to 1.0
    total = sum(dice_weights.values())
    if abs(total - 1.0) > 0.001:
        return False, f"Weights sum to {total:.3f}, expected 1.0"

    return True, "Valid"


def main():
    """Verify all preset configurations."""

    print("=" * 80)
    print("🎲 PRESET DICE WEIGHT VERIFICATION")
    print("=" * 80)
    print()

    all_valid = True

    for preset in PRESETS:
        preset_name = preset.get("name", preset.get("id"))
        print(f"{preset_name}")
        print("-" * len(preset_name))

        valid, message = verify_dice_weights(preset)

        if valid:
            print(f"✅ {message}")

            # Display weights
            dice_weights = preset.get("diceWeights", {})
            total = sum(dice_weights.values())

            print(f"\nDice Weights (Total: {total:.2f}):")

            # Sort by weight descending
            for dim, weight in sorted(dice_weights.items(), key=lambda x: -x[1]):
                pct = int(weight * 100)
                bar = "█" * (pct // 2)
                emoji = {
                    "what": "🟠",
                    "how": "🔴",
                    "when": "🟡",
                    "where": "🟢",
                    "who": "🔵",
                    "why": "🟣"
                }.get(dim, "⚪")
                print(f"  {emoji} {dim.upper():6s} ({pct:2d}%): {bar}")

            # Show optimizations
            optimized_for = preset.get("optimizedFor", [])
            if optimized_for:
                print(f"\nOptimized for: {', '.join(optimized_for[:3])}")
        else:
            print(f"❌ {message}")
            all_valid = False

        print()

    print("=" * 80)

    if all_valid:
        print("✅ All presets have valid dice weight configurations!")
        print("=" * 80)
        return 0
    else:
        print("❌ Some presets have invalid configurations")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
