import { Thread, ThreadAppearance } from "./models.js";

export type Layer = "green" | "yellow" | "orange" | "blue" | "purple" | "red";

export const layerPolicy: Record<Layer, string> = {
  green: "Grounding summaries only. Default layer.",
  yellow: "Exam orientation and timing cues.",
  orange: "Connections (max 3–5).",
  blue: "Single-thread explanation only.",
  purple: "Critique/essay prompts (time-limited).",
  red: "Safeguard collapse when stress is detected.",
};

const connectionLimit = 5;

export const enforceConnectionLimit = (connections: string[]): string[] =>
  connections.slice(0, connectionLimit);

export const shouldCollapseToRed = (stressSignals: number): boolean =>
  stressSignals >= 3;

export const nextThreadStage = (
  appearances: ThreadAppearance[],
): ThreadAppearance["label"] => {
  const labels = new Set(appearances.map((appearance) => appearance.label));
  if (!labels.has("definition")) return "definition";
  if (!labels.has("example")) return "example";
  if (!labels.has("expansion")) return "expansion";
  if (!labels.has("critique")) return "critique";
  return "application";
};

export const applySafeguards = (
  thread: Thread,
  stressSignals: number,
): Thread => {
  if (!shouldCollapseToRed(stressSignals)) {
    return thread;
  }
  return {
    ...thread,
    safeguards: {
      red_mode: true,
      reason: "Stress signals detected. Collapsing UI depth.",
      last_triggered: new Date().toISOString(),
    },
  };
};
