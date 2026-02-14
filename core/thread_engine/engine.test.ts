import test from "node:test"
import assert from "node:assert/strict"

import { initialiseFacets } from "./facets.js"
import { processThreadSegments } from "./engine.js"
import { DiceFace } from "./rotate.js"
import { initialiseFacets } from "./facets"
import { processThreadSegments } from "./engine"
import { DiceFace } from "./rotate"

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

test("interdisciplinary mode runs empirical and interpretive passes", () => {
  const facets = initialiseFacets()
  const callCounts: Record<DiceFace, number> = {
    RED: 0,
    ORANGE: 0,
    YELLOW: 0,
    GREEN: 0,
    BLUE: 0,
    PURPLE: 0,
  }

  const extractors = {
    RED: () => {
      callCounts.RED += 1
      return ["how"]
    },
    ORANGE: () => {
      callCounts.ORANGE += 1
      return ["what"]
    },
    YELLOW: () => {
      callCounts.YELLOW += 1
      return ["when"]
    },
    GREEN: () => {
      callCounts.GREEN += 1
      return ["where"]
    },
    BLUE: () => {
      callCounts.BLUE += 1
      return ["who"]
    },
    PURPLE: () => {
      callCounts.PURPLE += 1
      return ["why"]
    },
  }

  processThreadSegments({
    threadId: "thread-hybrid",
    segments: ["segment 1"],
    facets,
    extractors,
    mode: "INTERDISCIPLINARY",
  })

  for (const face of Object.keys(callCounts) as DiceFace[]) {
    assert.equal(callCounts[face], 2)
    assert.equal(facets[face].sourceCount, 2)
  }
})
