import { DiceFace } from "./rotate"

export interface FacetEvidence {
  snippets: string[]
  sourceCount: number
  lastUpdated: number
}

export interface ThreadFacets {
  RED: FacetEvidence
  ORANGE: FacetEvidence
  YELLOW: FacetEvidence
  GREEN: FacetEvidence
  BLUE: FacetEvidence
  PURPLE: FacetEvidence
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

export function initialiseFacets(): ThreadFacets {
  const emptyFacet = (): FacetEvidence => ({
    snippets: [],
    sourceCount: 0,
    lastUpdated: Date.now(),
  })

  return {
    RED: emptyFacet(),
    ORANGE: emptyFacet(),
    YELLOW: emptyFacet(),
    GREEN: emptyFacet(),
    BLUE: emptyFacet(),
    PURPLE: emptyFacet(),
  }
}

export function updateFacet(facets: ThreadFacets, face: DiceFace, snippet: string): ThreadFacets {
  const facet = facets[face]

  if (facet.snippets.length < MAX_SNIPPETS) {
    facet.snippets.push(snippet)
  }

  facet.sourceCount += 1
  facet.lastUpdated = Date.now()

  return facets
}

export function computeFacetScores(facets: ThreadFacets): FacetScores {
  const scores: Partial<FacetScores> = {}

  for (const face of Object.keys(facets) as DiceFace[]) {
    const facet = facets[face]

    const base = facet.snippets.length > 0 ? 0.2 : 0
    const evidenceBoost = facet.sourceCount * CONFIDENCE_INCREMENT
    const timeSinceUpdate = (Date.now() - facet.lastUpdated) / (1000 * 60 * 60)
    const decay = timeSinceUpdate * CONFIDENCE_DECAY
    const rawScore = base + evidenceBoost - decay

    scores[face] = Math.max(0, Math.min(CONFIDENCE_CAP, rawScore))
  }

  return scores as FacetScores
}
