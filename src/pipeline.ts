import {
  ExamSignal,
  Lecture,
  LectureSegment,
  Thread,
  ThreadAppearance,
} from "./models.js";
import { nextThreadStage } from "./architecture.js";
import { computeGravityScore } from "./scoring.js";

type ProcessedLectureInput = {
  lecture: Omit<Lecture, "segments" | "detected_threads" | "exam_signals">;
  rawTranscript: string;
  segments: LectureSegment[];
  detectedThreads: ThreadAppearance[];
  examSignals: ExamSignal[];
};

// Processing builds an immutable lecture record from verified inputs.
export const processLecture = ({
  lecture,
  rawTranscript,
  segments,
  detectedThreads,
  examSignals,
}: ProcessedLectureInput): Lecture => ({
  ...lecture,
  transcript: rawTranscript,
  segments,
  detected_threads: detectedThreads,
  exam_signals: examSignals,
});

type ThreadUpdateInput = {
  thread: Thread | null;
  appearances: ThreadAppearance[];
  examSignals: ExamSignal[];
  alignedToOutcomes: boolean;
  sourcesVerified: boolean;
};

// Threads are updated only when sources are verified to prevent hallucinations.
export const upsertThread = ({
  thread,
  appearances,
  examSignals,
  alignedToOutcomes,
  sourcesVerified,
}: ThreadUpdateInput): Thread => {
  if (!sourcesVerified) {
    throw new Error("Sources must be verified before updating threads.");
  }

  const existing = thread ?? {
    thread_id: crypto.randomUUID(),
    title: appearances[0]?.summary ?? "Untitled Thread",
    module_id: "",
    gravity_score: 0,
    confidence_score: 0,
    appearances: [],
    layers: {
      conscious: {
        summary: "",
        connections: [],
        critique_prompts: [],
        last_updated: new Date().toISOString(),
      },
      subconscious: {
        summary: "",
        connections: [],
        critique_prompts: [],
        last_updated: new Date().toISOString(),
      },
      unconscious: {
        summary: "",
        connections: [],
        critique_prompts: [],
        last_updated: new Date().toISOString(),
      },
    },
    exam_signals: [],
    sources: [],
    safeguards: {
      red_mode: false,
    },
  };

  const stagedAppearances = appearances.map((appearance) => ({
    ...appearance,
    label: appearance.label ?? nextThreadStage(existing.appearances),
  }));
  const updatedAppearances = [...existing.appearances, ...stagedAppearances];
  const updatedSignals = [...existing.exam_signals, ...examSignals];
  const gravity_score = computeGravityScore({
    appearanceCount: updatedAppearances.length,
    examSignals: updatedSignals,
    alignedToOutcomes,
  });

  return {
    ...existing,
    appearances: updatedAppearances,
    exam_signals: updatedSignals,
    gravity_score,
  };
};
