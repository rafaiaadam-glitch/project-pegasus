import test from "node:test"
import assert from "node:assert/strict"

import { rotatePerspective } from "./rotate.js"
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

test("collapse override prioritises weakest face in OPEN mode", () => {
test("collapse override prioritises weakest face", () => {
  const order = rotatePerspective({
    threadId: "thread-collapse",
    segmentIndex: 1,
    safeMode: true,
    mode: "OPEN",
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

test("collapse priority adapts to mode weights", () => {
  const order = rotatePerspective({
    threadId: "thread-mode-priority",
    segmentIndex: 2,
    mode: "MATHEMATICS",
    facetScores: {
      RED: 1,
      ORANGE: 0.4,
      YELLOW: 0.2,
      GREEN: 0.2,
      BLUE: 0,
      PURPLE: 0.1,
    },
  })

  assert.equal(order[0], "ORANGE")
})

test("interdisciplinary mode can favor empirical mix when collapsing", () => {
  const scores = {
    RED: 1,
    ORANGE: 0.5,
    YELLOW: 0.35,
    GREEN: 0.35,
    BLUE: 0.2,
    PURPLE: 0.2,
  }

  const empiricalOrder = rotatePerspective({
    threadId: "thread-hybrid-empirical",
    segmentIndex: 4,
    mode: "INTERDISCIPLINARY",
    empiricalMix: 0.85,
    facetScores: scores,
  })

  const interpretiveOrder = rotatePerspective({
    threadId: "thread-hybrid-interpretive",
    segmentIndex: 4,
    mode: "INTERDISCIPLINARY",
    empiricalMix: 0.15,
    facetScores: scores,
  })

  assert.equal(empiricalOrder[0], "GREEN")
  assert.equal(interpretiveOrder[0], "PURPLE")
})
