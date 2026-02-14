import test from "node:test"
import assert from "node:assert/strict"

import { rotatePerspective } from "./rotate"

test("deterministic permutation selection for same threadId and segmentIndex", () => {
  const first = rotatePerspective({ threadId: "thread-123", segmentIndex: 8 })
  const second = rotatePerspective({ threadId: "thread-123", segmentIndex: 8 })

  assert.deepEqual(first, second)
})

test("safeMode forces ORANGE then RED at the front", () => {
  const order = rotatePerspective({
    threadId: "thread-123",
    segmentIndex: 3,
    safeMode: true,
  })

  assert.equal(order[0], "ORANGE")
  assert.equal(order[1], "RED")
})

test("collapse override prioritises weakest face", () => {
  const order = rotatePerspective({
    threadId: "thread-collapse",
    segmentIndex: 1,
    safeMode: true,
    facetScores: {
      RED: 0.9,
      ORANGE: 0.6,
      YELLOW: 0.58,
      GREEN: 0.57,
      BLUE: 0.05,
      PURPLE: 0.56,
    },
  })

  assert.equal(order[0], "BLUE")
})
