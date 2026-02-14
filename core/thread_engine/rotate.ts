import permutations from "../dice/permutations.json" with { type: "json" }

export type DiceFace =
  | "RED"
  | "ORANGE"
  | "YELLOW"
  | "GREEN"
  | "BLUE"
  | "PURPLE"

export type LectureMode =
  | "MATHEMATICS"
  | "NATURAL_SCIENCE"
  | "SOCIAL_SCIENCE"
  | "HUMANITIES"
  | "OPEN"

export interface FacetScores {
  RED: number
  ORANGE: number
  YELLOW: number
  GREEN: number
  BLUE: number
  PURPLE: number
}

export interface RotateOptions {
  threadId: string
  segmentIndex: number
  facetScores?: FacetScores
  safeMode?: boolean
  mode?: LectureMode
  modeWeights?: Partial<FacetScores>
}

const GROUNDING_FACES: DiceFace[] = ["ORANGE", "RED"] // What + How
const COLLAPSE_GAP = 0.3

const FACE_TO_DIRECTION: Record<DiceFace, { label: string; number: number; direction: string }> = {
  RED: { label: "How", number: 1, direction: "South" },
  ORANGE: { label: "What", number: 2, direction: "Forward" },
  YELLOW: { label: "When", number: 3, direction: "North" },
  GREEN: { label: "Where", number: 4, direction: "Backward" },
  BLUE: { label: "Who", number: 5, direction: "West" },
  PURPLE: { label: "Why", number: 6, direction: "East" },
}

const OPEN_WEIGHTS: FacetScores = {
  RED: 0.166,
  ORANGE: 0.166,
  YELLOW: 0.166,
  GREEN: 0.166,
  BLUE: 0.166,
  PURPLE: 0.166,
}

export const MODE_FACE_WEIGHTS: Record<LectureMode, FacetScores> = {
  MATHEMATICS: {
    RED: 0.35,
    ORANGE: 0.35,
    YELLOW: 0.1,
    GREEN: 0.2,
    BLUE: 0,
    PURPLE: 0,
  },
  NATURAL_SCIENCE: {
    RED: 0.25,
    ORANGE: 0.2,
    YELLOW: 0.15,
    GREEN: 0.15,
    BLUE: 0.1,
    PURPLE: 0.15,
  },
  SOCIAL_SCIENCE: {
    RED: 0.2,
    ORANGE: 0.15,
    YELLOW: 0.15,
    GREEN: 0.15,
    BLUE: 0.2,
    PURPLE: 0.15,
  },
  HUMANITIES: {
    RED: 0.15,
    ORANGE: 0.15,
    YELLOW: 0.1,
    GREEN: 0.1,
    BLUE: 0.2,
    PURPLE: 0.3,
  },
  OPEN: OPEN_WEIGHTS,
}

export const DICE_FACE_DEFINITIONS = FACE_TO_DIRECTION

/** Deterministic hash function (stable across sessions). */
function simpleHash(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

function selectPermutation(threadId: string, segmentIndex: number): DiceFace[] {
  const schedule = permutations.schedule as DiceFace[][]
  const key = `${threadId}-${segmentIndex}`
  const index = simpleHash(key) % schedule.length
  return [...schedule[index]]
}

function detectCollapse(scores: FacetScores): boolean {
  const values = Object.values(scores)
  const sorted = [...values].sort((a, b) => b - a)
  const max = sorted[0]
  const median = sorted[Math.floor(sorted.length / 2)]
  return max - median >= COLLAPSE_GAP
}

function weakestFacet(scores: FacetScores): DiceFace {
  const values = Object.entries(scores) as [DiceFace, number][]
  values.sort((a, b) => a[1] - b[1])
  return values[0][0]
}

function stabiliseForSafeMode(order: DiceFace[]): DiceFace[] {
  const remaining = order.filter((face) => !GROUNDING_FACES.includes(face))
  return [...GROUNDING_FACES, ...remaining]
}

function normaliseWeights(weights: FacetScores): FacetScores {
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0)
  if (total <= 0) return OPEN_WEIGHTS

  return {
    RED: weights.RED / total,
    ORANGE: weights.ORANGE / total,
    YELLOW: weights.YELLOW / total,
    GREEN: weights.GREEN / total,
    BLUE: weights.BLUE / total,
    PURPLE: weights.PURPLE / total,
  }
}

function resolveWeights(mode?: LectureMode, override?: Partial<FacetScores>): FacetScores {
  const base = mode ? MODE_FACE_WEIGHTS[mode] : OPEN_WEIGHTS

  if (!override) {
    return base
  }

  const merged: FacetScores = {
    RED: override.RED ?? base.RED,
    ORANGE: override.ORANGE ?? base.ORANGE,
    YELLOW: override.YELLOW ?? base.YELLOW,
    GREEN: override.GREEN ?? base.GREEN,
    BLUE: override.BLUE ?? base.BLUE,
    PURPLE: override.PURPLE ?? base.PURPLE,
  }

  return normaliseWeights(merged)
}

function collapsePriorityFace(scores: FacetScores, weights: FacetScores): DiceFace {
  const maxScore = Math.max(...Object.values(scores))
  const weightedPriority = (Object.entries(scores) as [DiceFace, number][]).map(([face, score]) => {
    const gap = maxScore - score
    const weight = weights[face]
    return [face, weight * gap] as const
  })

  weightedPriority.sort((a, b) => b[1] - a[1])

  if (weightedPriority[0][1] === 0) {
    return weakestFacet(scores)
  }

  return weightedPriority[0][0]
}

export function rotatePerspective(options: RotateOptions): DiceFace[] {
  const { threadId, segmentIndex, facetScores, safeMode, mode, modeWeights } = options

  let permutation = selectPermutation(threadId, segmentIndex)

  if (facetScores && detectCollapse(facetScores)) {
    const weights = resolveWeights(mode, modeWeights)
    const prioritizedFace = collapsePriorityFace(facetScores, weights)
    permutation = [prioritizedFace, ...permutation.filter((face) => face !== prioritizedFace)]
    return permutation
  }

  if (safeMode) {
    permutation = stabiliseForSafeMode(permutation)
  }

  return permutation
}
