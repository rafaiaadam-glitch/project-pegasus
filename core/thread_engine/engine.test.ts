import test from "node:test"
import assert from "node:assert/strict"

import { initialiseFacets } from "./facets.js"
import { processThreadSegments } from "./engine.js"
import { DiceFace } from "./rotate.js"

test("thread engine processes extractors in rotatePerspective order", () => {
  const facets = initialiseFacets()
  const called: DiceFace[] = []

  const extractors = {
    RED: () => {
      called.push("RED")
      return ["how"]
    },
    ORANGE: () => {
      called.push("ORANGE")
      return ["what"]
    },
    YELLOW: () => {
      called.push("YELLOW")
      return ["when"]
    },
    GREEN: () => {
      called.push("GREEN")
      return ["where"]
    },
    BLUE: () => {
      called.push("BLUE")
      return ["who"]
    },
    PURPLE: () => {
      called.push("PURPLE")
      return ["why"]
    },
  }

  processThreadSegments({
    threadId: "thread-ordered",
    segments: ["segment 1"],
    facets,
    extractors,
    safeMode: true,
  })

  assert.equal(called[0], "ORANGE")
  assert.equal(called[1], "RED")
  assert.equal(facets.ORANGE.sourceCount, 1)
  assert.equal(facets.RED.sourceCount, 1)
})
