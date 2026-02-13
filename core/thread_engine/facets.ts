// core/thread_engine/facets.ts

import { DiceFace } from "./rotate"

export interface FacetEvidence {
  snippets: string[]          // extracted text fragments
  sourceCount: number         // number of distinct segments supporting it
  lastUpdated: number         // timestamp
}

export interface ThreadFacets {
  RED: FacetEvidence      // How
  ORANGE: FacetEvidence   // What
  YELLOW: FacetEvidence   // When
  GREEN: FacetEvidence    // Where
  BLUE: FacetEvidence     // Who
  PURPLE: FacetEvidence   // Why
}

export interface FacetScores {
  RED: number
  ORANGE: number
  YELLOW: number
  GREEN: number
  BLUE: number
  PURPLE: number
}

const MAX_SNIPPETS = 10
const CONFIDENCE_CAP = 1.0
const CONFIDENCE_INCREMENT = 0.08
const CONFIDENCE_DECAY = 0.02
