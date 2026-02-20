import { DiceFace } from "./rotate"
import { ThreadFacets } from "./facets"
import { SegmentContext, AsyncFacetExtractors } from "./engine"
import { ChatMessage, LLMCompleter } from "./types"

const FACE_PROMPTS: Record<DiceFace, { focus: string; instruction: string }> = {
  RED: {
    focus: "How (Mechanisms)",
    instruction: "Extract specific mechanisms, processes, or methods described in this text segment. Return each as a short bullet point on its own line.",
  },
  ORANGE: {
    focus: "What (Definitions)",
    instruction: "Extract key definitions, concepts, and factual claims from this text segment. Return each as a short bullet point on its own line.",
  },
  YELLOW: {
    focus: "When (Temporal)",
    instruction: "Extract temporal markers, sequences, and chronological context from this text segment. Return each as a short bullet point on its own line.",
  },
  GREEN: {
    focus: "Where (Spatial/Domain)",
    instruction: "Extract spatial, geographical, or domain-specific context from this text segment. Return each as a short bullet point on its own line.",
  },
  BLUE: {
    focus: "Who (Actors)",
    instruction: "Extract people, stakeholders, authors, or attributed sources from this text segment. Return each as a short bullet point on its own line.",
  },
  PURPLE: {
    focus: "Why (Reasoning)",
    instruction: "Extract reasoning, causes, motivations, and justifications from this text segment. Return each as a short bullet point on its own line.",
  },
}

function parseSnippets(response: string): string[] {
  return response
    .split("\n")
    .map((line) => line.replace(/^[-*•]\s*/, "").trim())
    .filter((line) => line.length > 0)
}

export function createFacetExtractors(completer: LLMCompleter): AsyncFacetExtractors {
  const faces: DiceFace[] = ["RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "PURPLE"]

  const extractors = {} as AsyncFacetExtractors

  for (const face of faces) {
    const { focus, instruction } = FACE_PROMPTS[face]

    extractors[face] = async (segment: SegmentContext, _facets: ThreadFacets): Promise<string[]> => {
      const messages: ChatMessage[] = [
        {
          role: "system",
          content: `You are an evidence extractor focused on the "${focus}" dimension.\n${instruction}\nIf no relevant evidence is found, respond with "NONE".`,
        },
        {
          role: "user",
          content: segment.text,
        },
      ]

      const response = await completer(messages)

      if (response.trim().toUpperCase() === "NONE") {
        return []
      }

      return parseSnippets(response)
    }
  }

  return extractors
}
