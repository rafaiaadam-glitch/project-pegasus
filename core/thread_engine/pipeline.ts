import { initialiseFacets, ThreadFacets } from "./facets"
import { processThreadSegmentsAsync } from "./engine"
import { createFacetExtractors } from "./extractors"
import { LectureMode } from "./rotate"
import { LLMCompleter } from "./types"

const DEFAULT_CHUNK_SIZE = 500

export interface ProcessTranscriptOptions {
  mode?: LectureMode
  safeMode?: boolean
  chunkSize?: number
}

function splitIntoSegments(transcript: string, chunkSize: number): string[] {
  const paragraphs = transcript.split(/\n\n+/).filter((p) => p.trim().length > 0)

  const segments: string[] = []
  let buffer = ""

  for (const paragraph of paragraphs) {
    if (buffer.length + paragraph.length > chunkSize && buffer.length > 0) {
      segments.push(buffer.trim())
      buffer = ""
    }
    buffer += (buffer ? "\n\n" : "") + paragraph
  }

  if (buffer.trim().length > 0) {
    segments.push(buffer.trim())
  }

  return segments
}

export function createDiceEngine(completer: LLMCompleter) {
  const extractors = createFacetExtractors(completer)

  return {
    async processTranscript(
      transcript: string,
      threadId: string,
      options: ProcessTranscriptOptions = {},
    ): Promise<ThreadFacets> {
      const { mode, safeMode, chunkSize = DEFAULT_CHUNK_SIZE } = options
      const segments = splitIntoSegments(transcript, chunkSize)
      const facets = initialiseFacets()

      return processThreadSegmentsAsync({
        threadId,
        segments,
        facets,
        extractors,
        safeMode,
        mode,
      })
    },
  }
}
