// core/dice/permutations.ts

export type DiceFace =
  | "RED"
  | "ORANGE"
  | "YELLOW"
  | "GREEN"
  | "BLUE"
  | "PURPLE"

export const BASE_FACES: DiceFace[] = [
  "RED",
  "ORANGE",
  "YELLOW",
  "GREEN",
  "BLUE",
  "PURPLE",
]

/**
 * Heap's Algorithm for generating all permutations
 * Deterministic and complete (720 states for 6 elements)
 */
export function generatePermutations(
  faces: DiceFace[] = BASE_FACES
): DiceFace[][] {

  const results: DiceFace[][] = []
  const arr = [...faces]

  function heap(n: number) {
    if (n === 1) {
      results.push([...arr])
      return
    }

    heap(n - 1)

    for (let i = 0; i < n - 1; i++) {
      if (n % 2 === 0) {
        ;[arr[i], arr[n - 1]] = [arr[n - 1], arr[i]]
      } else {
        ;[arr[0], arr[n - 1]] = [arr[n - 1], arr[0]]
      }
      heap(n - 1)
    }
  }

  heap(arr.length)

  return results
}
