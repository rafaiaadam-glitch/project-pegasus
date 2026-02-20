import { HYBRID_WEIGHTS } from "../dice/courseModes"
import { computeFacetScores, ThreadFacets, updateFacet } from "./facets"
import { DiceFace, LectureMode, FacetScores, rotatePerspective } from "./rotate"

export interface SegmentContext {
  text: string
  index: number
}

export type FacetExtractor = (segment: SegmentContext, facets: ThreadFacets) => string[]
export type AsyncFacetExtractor = (segment: SegmentContext, facets: ThreadFacets) => Promise<string[]>

export type FacetExtractors = Record<DiceFace, FacetExtractor>
export type AsyncFacetExtractors = Record<DiceFace, AsyncFacetExtractor>

export interface ProcessThreadSegmentsOptions {
  threadId: string
  segments: string[]
  facets: ThreadFacets
  extractors: FacetExtractors
  safeMode?: boolean
  mode?: LectureMode
  modeWeights?: Partial<FacetScores>
  empiricalMix?: number
}

/**
 * Mandatory Dice control-flow execution for Thread Engine segment processing.
 */
export function processThreadSegments(options: ProcessThreadSegmentsOptions): ThreadFacets {
  const { threadId, segments, facets, extractors, safeMode, mode, modeWeights, empiricalMix } = options

  for (const [segmentIndex, text] of segments.entries()) {
    const runPass = (passWeights?: Partial<FacetScores>) => {
      const facetScores = computeFacetScores(facets)
      const order = rotatePerspective({
        threadId,
        segmentIndex,
        facetScores,
        safeMode,
        mode,
        modeWeights: passWeights,
        empiricalMix,
      })

      for (const face of order) {
        const extractor = extractors[face]
        const snippets = extractor({ text, index: segmentIndex }, facets)

        for (const snippet of snippets) {
          updateFacet(facets, face, snippet)
        }
      }
    }

    if (mode === "INTERDISCIPLINARY") {
      runPass(HYBRID_WEIGHTS.EMPIRICAL)
      runPass(HYBRID_WEIGHTS.INTERPRETIVE)
      continue
    }

    runPass(modeWeights)
  }

  return facets
}

export interface ProcessThreadSegmentsAsyncOptions {
  threadId: string
  segments: string[]
  facets: ThreadFacets
  extractors: AsyncFacetExtractors
  safeMode?: boolean
  mode?: LectureMode
  modeWeights?: Partial<FacetScores>
  empiricalMix?: number
}

/**
 * Async variant of processThreadSegments that awaits each extractor call.
 * Uses the same dice rotation logic as the sync version.
 */
export async function processThreadSegmentsAsync(options: ProcessThreadSegmentsAsyncOptions): Promise<ThreadFacets> {
  const { threadId, segments, facets, extractors, safeMode, mode, modeWeights, empiricalMix } = options

  for (const [segmentIndex, text] of segments.entries()) {
    const runPass = async (passWeights?: Partial<FacetScores>) => {
      const facetScores = computeFacetScores(facets)
      const order = rotatePerspective({
        threadId,
        segmentIndex,
        facetScores,
        safeMode,
        mode,
        modeWeights: passWeights,
        empiricalMix,
      })

      for (const face of order) {
        const extractor = extractors[face]
        const snippets = await extractor({ text, index: segmentIndex }, facets)

        for (const snippet of snippets) {
          updateFacet(facets, face, snippet)
        }
      }
    }

    if (mode === "INTERDISCIPLINARY") {
      await runPass(HYBRID_WEIGHTS.EMPIRICAL)
      await runPass(HYBRID_WEIGHTS.INTERPRETIVE)
      continue
    }

    await runPass(modeWeights)
  }

  return facets
}
