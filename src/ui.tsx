import React from "react";
import { Thread } from "./models.js";
import { computePriority } from "./scoring.js";

type Layer = "green" | "yellow" | "orange";

// Layer labels communicate depth without overwhelming detail.
const layerCopy: Record<Layer, string> = {
  green: "Grounding summary",
  yellow: "Exam orientation",
  orange: "Connections",
};

// ThreadCard enforces bounded depth and explicit user action for deeper layers.
export const ThreadCard: React.FC<{
  thread: Thread;
  activeLayer: Layer;
  onRequestDeeperLayer: (layer: Layer) => void;
}> = ({ thread, activeLayer, onRequestDeeperLayer }) => {
  const priority = computePriority(thread);
  return (
    <section aria-label={`Thread ${thread.title}`}>
      <header>
        <h3>{thread.title}</h3>
        <p>{layerCopy[activeLayer]}</p>
      </header>
      <p>{thread.layers.conscious.summary}</p>
      <p>Priority: {(priority * 100).toFixed(0)}%</p>
      <div>
        {activeLayer !== "yellow" && (
          <button onClick={() => onRequestDeeperLayer("yellow")}>
            View exam timing
          </button>
        )}
        {activeLayer !== "orange" && (
          <button onClick={() => onRequestDeeperLayer("orange")}>
            View connections
          </button>
        )}
      </div>
    </section>
  );
};

// StudyTodayView keeps GREEN as the default layer for calm focus.
export const StudyTodayView: React.FC<{
  threads: Thread[];
  activeLayer: Layer;
  onRequestDeeperLayer: (layer: Layer) => void;
}> = ({ threads, activeLayer, onRequestDeeperLayer }) => {
  const ordered = [...threads].sort(
    (a, b) => computePriority(b) - computePriority(a),
  );

  return (
    <main>
      <h2>What to Study Today</h2>
      <p>Default layer is GREEN to protect attention.</p>
      {ordered.map((thread) => (
        <ThreadCard
          key={thread.thread_id}
          thread={thread}
          activeLayer={activeLayer}
          onRequestDeeperLayer={onRequestDeeperLayer}
        />
      ))}
    </main>
  );
};
