import test from "node:test"
import assert from "node:assert/strict"

import { getHybridCombinedWeights, getModeWeights } from "../dice/courseModes.js"

test("interdisciplinary mode resolves to normalized hybrid weights", () => {
  const weights = getModeWeights("INTERDISCIPLINARY", { empiricalMix: 0.5 })
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0)

  assert.ok(Math.abs(total - 1) < 1e-9)
})

test("hybrid mix clamps outside [0,1]", () => {
  const empirical = getHybridCombinedWeights(3)
  const interpretive = getHybridCombinedWeights(-2)
  const empiricalBase = getModeWeights("INTERDISCIPLINARY", { empiricalMix: 1 })
  const interpretiveBase = getModeWeights("INTERDISCIPLINARY", { empiricalMix: 0 })

  assert.deepEqual(empirical, empiricalBase)
  assert.deepEqual(interpretive, interpretiveBase)
})
