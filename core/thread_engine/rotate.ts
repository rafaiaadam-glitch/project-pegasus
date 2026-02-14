// core/thread_engine/rotate.ts

import { generatePermutations } from "../dice/permutations"

const ALL_PERMUTATIONS = generatePermutations()

function selectPermutation(threadId: string, segmentIndex: number) {
  const key = `${threadId}-${segmentIndex}`
  const hash = simpleHash(key)
  const index = hash % ALL_PERMUTATIONS.length
  return [...ALL_PERMUTATIONS[index]]
}

export type DiceFace =
  | "RED"
  | "ORANGE"
  | "YELLOW"
  | "GREEN"
  | "BLUE"
  | "PURPLE"

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
}

const GROUNDING_FACES: DiceFace[] = ["ORANGE", "RED"] // What + How

const EPSILON = 0.2   // equilibrium band
const COLLAPSE_GAP = 0.3

/**
 * Deterministic hash function (stable across sessions)
 */
function simpleHash(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

/**
 * Select permutation deterministically
 */
function selectPermutation(threadId: string, segmentIndex: number): DiceFace[] {
  const schedule: DiceFace[][] = permutations.schedule
  const key = `${threadId}-${segmentIndex}`
  const index = simpleHash(key) % schedule.length
  return [...schedule[index]]
}

/**
 * Detect collapse in facet scores
 */
function detectCollapse(scores: FacetScores): DiceFace | null {
  const values = Object.entries(scores)
  const sorted = [...values].sort((a, b) => b[1] - a[1])

  const max = sorted[0][1]
  const median = sorted[Math.floor(sorted.length / 2)][1]

  if (max - median >= COLLAPSE_GAP) {
    return sorted[0][0] as DiceFace
  }

  return null
}

/**
 * Detect weakest facet
 */
function weakestFacet(scores: FacetScores): DiceFace {
  const values = Object.entries(scores)
  values.sort((a, b) => a[1] - b[1])
  return values[0][0] as DiceFace
}

/**
 * Stabilise permutation for safe mode
 */
function stabiliseForSafeMode(order: DiceFace[]): DiceFace[] {
  const remaining = order.filter(face => !GROUNDING_FACES.includes(face))
  return [...GROUNDING_FACES, ...remaining]
}

/**
 * Main rotate function
 */
export function rotatePerspective(options: RotateOptions): DiceFace[] {
  const { threadId, segmentIndex, facetScores, safeMode } = options

  let permutation = selectPermutation(threadId, segmentIndex)

  // Collapse override
  if (facetScores) {
    const collapsed = detectCollapse(facetScores)

    if (collapsed) {
      const weakest = weakestFacet(facetScores)
      // Force weakest facet to front
      permutation = [
        weakest,
        ...permutation.filter(face => face !== weakest),
      ]
      return permutation
    }
  }

  // Safe mode override
  if (safeMode) {
    permutation = stabiliseForSafeMode(permutation)
  }

  return permutation
}
