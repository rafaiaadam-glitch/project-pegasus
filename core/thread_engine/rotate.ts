import permutations from "../dice/permutations.json"

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

/**
 * The only ordering decision point for the Thread Engine.
 */
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

export function rotatePerspective(options: RotateOptions): DiceFace[] {
  const { threadId, segmentIndex, facetScores, safeMode, mode, modeWeights } = options

  let permutation = selectPermutation(threadId, segmentIndex)

  if (facetScores && detectCollapse(facetScores)) {
    const weakest = weakestFacet(facetScores)
    permutation = [weakest, ...permutation.filter((face) => face !== weakest)]
    return permutation
  }

  if (safeMode) {
    permutation = stabiliseForSafeMode(permutation)
  }

  return permutation
}
