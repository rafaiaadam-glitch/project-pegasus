import { ExamSignal, Thread } from "./models.js";

// Clamp scores to keep UI predictable and explainable.
const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

export type GravityInputs = {
  appearanceCount: number;
  examSignals: ExamSignal[];
  alignedToOutcomes: boolean;
  pastPaperBoost?: number;
};

export type ConfidenceInputs = {
  recallScore: number;
  explanationDepth: number;
  timeDecay: number;
  selfRating: number;
};

// Gravity answers "How risky is it to ignore this?"
export const computeGravityScore = ({
  appearanceCount,
  examSignals,
  alignedToOutcomes,
  pastPaperBoost = 0,
}: GravityInputs): number => {
  const frequencyScore = Math.min(appearanceCount / 6, 1);
  const signalScore = examSignals.reduce(
    (total, signal) => total + signal.weight,
    0,
  );
  const outcomeBoost = alignedToOutcomes ? 0.2 : 0;
  const raw =
    0.5 * frequencyScore +
    0.3 * clamp(signalScore / 3, 0, 1) +
    outcomeBoost +
    pastPaperBoost;
  return clamp(raw, 0, 1);
};

// Confidence answers "Can the student answer this under pressure?"
export const computeConfidenceScore = ({
  recallScore,
  explanationDepth,
  timeDecay,
  selfRating,
}: ConfidenceInputs): number => {
  const raw =
    0.35 * recallScore +
    0.35 * explanationDepth +
    0.2 * selfRating -
    0.1 * timeDecay;
  return clamp(raw, 0, 1);
};

// Priority drives ordering and alerts without overloading the student.
export const computePriority = (thread: Thread): number =>
  clamp(thread.gravity_score * (1 - thread.confidence_score), 0, 1);
