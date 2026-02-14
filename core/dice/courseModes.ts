export type DiceFace = "RED" | "ORANGE" | "YELLOW" | "GREEN" | "BLUE" | "PURPLE"

export type CourseMode =
  | "MATHEMATICS"
  | "NATURAL_SCIENCE"
  | "SOCIAL_SCIENCE"
  | "HUMANITIES"
  | "INTERDISCIPLINARY"
  | "OPEN"

export type FaceWeights = Record<DiceFace, number>

export type HybridProfile = "EMPIRICAL" | "INTERPRETIVE"

const normalize = (weights: FaceWeights): FaceWeights => {
  const sum = Object.values(weights).reduce((acc, value) => acc + value, 0)

  if (sum === 0) {
    return weights
  }

  return Object.fromEntries(
    Object.entries(weights).map(([key, value]) => [key, value / sum]),
  ) as FaceWeights
}

const clamp01 = (value: number): number => Math.max(0, Math.min(1, value))

export const MODE_WEIGHTS: Record<CourseMode, FaceWeights> = {
  MATHEMATICS: normalize({
    ORANGE: 0.35,
    RED: 0.35,
    GREEN: 0.2,
    YELLOW: 0.1,
    BLUE: 0,
    PURPLE: 0,
  }),
  NATURAL_SCIENCE: normalize({
    ORANGE: 0.2,
    RED: 0.25,
    YELLOW: 0.15,
    GREEN: 0.15,
    BLUE: 0.1,
    PURPLE: 0.15,
  }),
  SOCIAL_SCIENCE: normalize({
    ORANGE: 0.15,
    RED: 0.2,
    YELLOW: 0.15,
    GREEN: 0.15,
    BLUE: 0.2,
    PURPLE: 0.15,
  }),
  HUMANITIES: normalize({
    ORANGE: 0.15,
    RED: 0.15,
    YELLOW: 0.1,
    GREEN: 0.1,
    BLUE: 0.2,
    PURPLE: 0.3,
  }),
  INTERDISCIPLINARY: normalize({
    ORANGE: 0.16,
    RED: 0.2,
    YELLOW: 0.14,
    GREEN: 0.14,
    BLUE: 0.18,
    PURPLE: 0.18,
  }),
  OPEN: normalize({
    ORANGE: 1,
    RED: 1,
    YELLOW: 1,
    GREEN: 1,
    BLUE: 1,
    PURPLE: 1,
  }),
}

export const HYBRID_WEIGHTS: Record<HybridProfile, FaceWeights> = {
  EMPIRICAL: normalize({
    ORANGE: 0.18,
    RED: 0.28,
    YELLOW: 0.18,
    GREEN: 0.18,
    BLUE: 0.1,
    PURPLE: 0.08,
  }),
  INTERPRETIVE: normalize({
    ORANGE: 0.16,
    RED: 0.16,
    YELLOW: 0.08,
    GREEN: 0.1,
    BLUE: 0.22,
    PURPLE: 0.28,
  }),
}

export function getHybridCombinedWeights(empiricalMix = 0.5): FaceWeights {
  const empirical = HYBRID_WEIGHTS.EMPIRICAL
  const interpretive = HYBRID_WEIGHTS.INTERPRETIVE
  const mix = clamp01(empiricalMix)

  const combined: FaceWeights = {
    RED: empirical.RED * mix + interpretive.RED * (1 - mix),
    ORANGE: empirical.ORANGE * mix + interpretive.ORANGE * (1 - mix),
    YELLOW: empirical.YELLOW * mix + interpretive.YELLOW * (1 - mix),
    GREEN: empirical.GREEN * mix + interpretive.GREEN * (1 - mix),
    BLUE: empirical.BLUE * mix + interpretive.BLUE * (1 - mix),
    PURPLE: empirical.PURPLE * mix + interpretive.PURPLE * (1 - mix),
  }

  return normalize(combined)
}

export function getModeWeights(mode: CourseMode, opts?: { empiricalMix?: number }): FaceWeights {
  if (mode === "INTERDISCIPLINARY") {
    return getHybridCombinedWeights(opts?.empiricalMix ?? 0.5)
  }

  return MODE_WEIGHTS[mode]
}
